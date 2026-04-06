from __future__ import annotations
import json
import re
import socket
import time
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

RUTA_BD = Path(__file__).with_name("clients_db.json")
db_lock = threading.Lock()

def _cargar_bd() -> dict:
    with db_lock:
        if not RUTA_BD.exists(): 
            return {"clients": []}
        with RUTA_BD.open("r", encoding="utf-8") as archivo:
            return json.load(archivo)

def _guardar_bd(bd: dict) -> None:
    with db_lock:
        with RUTA_BD.open("w", encoding="utf-8") as archivo:
            json.dump(bd, archivo, ensure_ascii=False, indent=2)

def _actualizar_bd(nombre_usuario: str, nuevo_saldo: float, acciones: list[dict]) -> None:
    bd = _cargar_bd()
    for cliente in bd.get("clients", []):
        if cliente.get("username") == nombre_usuario:
            cliente["balance"] = float(nuevo_saldo)
            partes = []
            for accion in acciones:
                acc, cant = accion["action"], accion["amount"]
                if acc == 1: partes.append("1")
                else:
                    cant_str = str(int(cant)) if float(cant).is_integer() else str(cant)
                    partes.append(f"{acc} {cant_str}")
            
            cliente.setdefault("batches_done", []).append({
                "batch": ",".join(partes),
                "datetime": datetime.now().isoformat(timespec="seconds")
            })
            break
    _guardar_bd(bd)

class GestorLotes:
    def __init__(self):
        self.lotes = {}  # {lote_id: {"user": str, "ops": [], "status": str}}

    def crear_lote(self, usuario: str) -> str:
        lote_id = str(uuid.uuid4())[:8]  # ID único
        self.lotes[lote_id] = {"user": usuario, "ops": [], "status": "PREPARACION"}
        return lote_id

gestor_lotes= GestorLotes()

def _enviar(conexion: socket.socket, texto: str) -> None:
    conexion.sendall((texto if texto else "\n").encode("utf-8"))

def _recibir(conexion: socket.socket) -> Optional[str]:
    try:
        datos = conexion.recv(4096)
        return datos.decode("utf-8", errors="replace").strip() if datos else None
    except Exception:
        return None

def manejar_cliente(conexion: socket.socket, direccion: tuple[str, int]) -> None:
    print(f"[+] Nueva conexión: {direccion}")
    try:
        estado = 0  # 0=USUARIO, 1=CLAVE, 2=LOTE, 3=CONFIRMAR
        user_session = ""
        lote_id = ""
        pendiente = {"id": "", "lote": [], "saldo": 0.0}
        while True:
            match estado:
                case 0:  # PEDIR_USUARIO
                    logo = r"""
  ____                       
 |  _ \                      
 | |_) | __ _ _ __   ___ ___ 
 |  _ < / _` | '_ \ / __/ _ \
 | |_) | (_| | | | | (_| (_) |
 |____/ \__,_|_| |_|\___\___/

"""
                    _enviar(conexion, f"{logo}introduzca su usuario: ")
                    entrada = _recibir(conexion)
                    if entrada is None: return
                    if not entrada: continue
                    
                    if not re.fullmatch(r"[A-Za-z0-9_-]+", entrada) or len(entrada) > 64:
                        _enviar(conexion, "\n[!] error: el nombre de usuario tiene caracteres no permitidos o es muy largo\n"); continue
                        
                    bd = _cargar_bd()
                    datos_usuario = next((c for c in bd.get("clients", []) if c.get("username") == entrada), None)
                    if not datos_usuario:
                        _enviar(conexion, "\n[!] usuario no existe\n"); continue
                    user_session = entrada                        
                    estado = 1

                case 1:  # PEDIR_CONTRASENA
                    _enviar(conexion, "\nintroduzca su contraseña: ")
                    pwd = _recibir(conexion)
                    if pwd is None: return
                    if not pwd: continue
                    
                    if len(pwd) > 64 or any(c.isspace() for c in pwd):
                        _enviar(conexion, "\n[!] error: la contrasena tiene caracteres no permitidos o es muy larga\n")
                        estado = 0; continue
                        
                    if datos_usuario.get("password") != pwd:
                        _enviar(conexion, "\n[!] contraseña incorrecta\n")
                        estado = 0; continue
                        
                    autenticado_en = time.monotonic()
                    estado = 2

                case 2:  # PEDIR_LOTE
                    _enviar(conexion, "\nlote (acciones separadas por ','). 1=saldo | 2 <cantidad>=ingresar | 3 <cantidad>=retirar | 4=cerrar sesion: ")
                    entrada = _recibir(conexion)
                    if entrada is None: return
                    if not entrada: continue

                    if entrada.strip() == "4":
                        _enviar(conexion, "\n¡Hasta pronto!\n")
                        estado = 0
                        continue
                    
                    # Comprobamos la inactividad de la sesión (120 seg)
                    if time.monotonic() - autenticado_en > 720.0:
                        _enviar(conexion, "\n[!] sesion expirada\n")
                        estado = 0
                        continue
                        
                    if len(entrada) > 256 or not re.fullmatch(r"[A-Za-z0-9 _.,;:/@#()-]+", entrada):
                        _enviar(conexion, "\n[!] error: el lote contiene caracteres invalidos\n"); continue
                        
                    acciones_bruto = [p.strip() for p in entrada.split(",")]
                    if any(not p for p in acciones_bruto) or len(acciones_bruto) > 3:
                        _enviar(conexion, "\n[!] error: el formato del lote no es valido o supera las 3 acciones maximas\n"); continue
                        
                    bd = _cargar_bd()
                    u = next(c for c in bd["clients"] if c["username"] == user_session)
                    saldo_temp = float(u.get("balance", 0.0))
                    acciones_validas, errores = [], []
                    
                    for a in acciones_bruto:
                        partes = a.split()
                        acc = partes[0]
                        if acc not in ("1", "2", "3", "4") or (acc == "1" and len(partes) != 1) or (acc in ("2", "3") and len(partes) != 2):
                            errores.append("\n[!] error: accion desconocida o numero de parametros incorrecto\n"); continue
                            
                        cant = 0.0
                        if acc in ("2", "3"):
                            try:
                                cant = float(partes[1].replace(",", "."))
                                if cant < 0: raise ValueError
                            except ValueError:
                                errores.append("\n[!] error: la cantidad introducida no es valida\n"); continue
                                
                        if acc == "2":
                            saldo_temp += cant
                        elif acc == "3":
                            if cant > saldo_temp:
                                errores.append(f"\n[!] accion {acc} no tienes suficiente dinero en tu cuenta\n"); continue
                            saldo_temp -= cant
                            
                        acciones_validas.append({"action": int(acc), "amount": cant})
                        
                    if errores:
                        _enviar(conexion, "\n".join(errores))
                    
                    if not acciones_validas:
                        continue

                    lote_id = gestor_lotes.crear_lote(user_session)
                    pendiente.update({"id": lote_id, "lote": acciones_validas, "saldo": saldo_temp})
                    _enviar(conexion, f"\n[OK] Lote '{lote_id}' preparado con {len(acciones_validas)} acciones.")
                    estado = 3

                case 3:  # CONFIRMAR_LOTE
                    _enviar(conexion, "\nconfirmar? (si/no): ")
                    entrada = _recibir(conexion)
                    if entrada is None: return
                    if not entrada: continue

                    # Comprobamos la inactividad de la sesión (120 seg)
                    if time.monotonic() - autenticado_en > 720.0:
                        _enviar(conexion, "\n[!] sesion expirada\n")
                        estado = 1
                        continue
                    
                    if entrada.lower() in ("si", "s", "yes", "y"):
                        datos_usuario["balance"] = pendiente["saldo"]
                        _actualizar_bd(datos_usuario["username"], pendiente["saldo"], pendiente["lote"])
                        _enviar(conexion, f"\n[+] acciones realizadas ({len(pendiente['lote'])}). balance={pendiente['saldo']}\n")
                        mensajes_finales = []
                        for op in pendiente["lote"]:
                            texto_accion = "" 
                            
                            if op["action"] == 1:
                                texto_accion = f"Su saldo es {pendiente['saldo']}"
                            elif op["action"] == 2:
                                texto_accion = f"Ha ingresado {op['amount']}"
                            elif op["action"] == 3:
                                texto_accion = f"Ha retirado {op['amount']}"
                            
                            if texto_accion:
                                mensajes_finales.append(texto_accion)
                                print(f"[LOG - {user_session}]: {texto_accion}")

                        respuesta_completa = "\n".join(mensajes_finales)
                        _enviar(conexion, f"\n{respuesta_completa}\n[OK] Operación finalizada.\n")
                    else:
                        _enviar(conexion, "\n[-] Lote cancelado y liberado. \n")
                        
                    estado = 2

    finally:
        try:
            conexion.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conexion.close()

def iniciar_servidor(host: str = "127.0.0.1", puerto: int = 6345) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, puerto))
        s.listen()
        print(f"Servidor iniciado y escuchando en el puerto {puerto}...")
        while True:
            conexion, direccion = s.accept()
            hilo = threading.Thread(target=manejar_cliente, args=(conexion, direccion))
            hilo.start()

if __name__ == "__main__":
    #iniciar_servidor()
    iniciar_servidor(host="0.0.0.0", puerto=6345)