from __future__ import annotations

import json
import re
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

RUTA_BD = Path(__file__).with_name("clients_db.json")

def _cargar_bd() -> dict:
    with RUTA_BD.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)

def _actualizar_bd(nombre_usuario: str, nuevo_saldo: float, acciones: list[dict]) -> None:
    bd = _cargar_bd()
    for cliente in bd.get("clients", []):
        if cliente.get("username") == nombre_usuario:
            cliente["balance"] = float(nuevo_saldo)
            partes = []
            for accion in acciones:
                acc, cant = accion["action"], accion["amount"]
                if acc == 1:
                    partes.append("1")
                else:
                    cant_str = str(int(cant)) if float(cant).is_integer() else str(cant)
                    partes.append(f"{acc} {cant_str}")
                    
            cliente.setdefault("batches_done", []).append({
                "batch": ",".join(partes),
                "username": nombre_usuario,
                "datetime": datetime.now().isoformat(timespec="seconds")
            })
            break
            
    with RUTA_BD.open("w", encoding="utf-8") as archivo:
        json.dump(bd, archivo, ensure_ascii=False, indent=2)

def _enviar(conexion: socket.socket, texto: str) -> None:
    conexion.sendall((texto if texto else "\n").encode("utf-8"))

def _recibir(conexion: socket.socket) -> Optional[str]:
    try:
        datos = conexion.recv(4096)
        return datos.decode("utf-8", errors="replace").strip() if datos else None
    except Exception:
        return None

def manejar_cliente(conexion: socket.socket, direccion: tuple[str, int]) -> None:
    try:
        # ¡Temporizador eliminado! Ahora espera pacientemente.
        estado = 0  # 0=USUARIO, 1=CLAVE, 2=LOTE, 3=CONFIRMAR
        autenticado_en = 0.0
        datos_usuario = {}
        pendiente = {"lote": [], "saldo": 0.0}

        while True:
            match estado:
                case 0:  # PEDIR_USUARIO
                    _enviar(conexion, "introduzca su usuario: ")
                    entrada = _recibir(conexion)
                    if entrada is None: return
                    if not entrada: continue
                    
                    if not re.fullmatch(r"[A-Za-z0-9_-]+", entrada) or len(entrada) > 64:
                        _enviar(conexion, "error 404 input no valido"); continue
                        
                    bd = _cargar_bd()
                    datos_usuario = next((c for c in bd.get("clients", []) if c.get("username") == entrada), None)
                    if not datos_usuario:
                        _enviar(conexion, "usuario no existe"); continue
                        
                    estado = 1

                case 1:  # PEDIR_CONTRASENA
                    _enviar(conexion, "introduzca su contraseña: ")
                    entrada = _recibir(conexion)
                    if entrada is None: return
                    if not entrada: continue
                    
                    if len(entrada) > 64 or any(c.isspace() for c in entrada):
                        _enviar(conexion, "error 404 input no valido")
                        estado = 0; continue
                        
                    if datos_usuario.get("password") != entrada:
                        _enviar(conexion, "contraseña incorrecta")
                        estado = 0; continue
                        
                    autenticado_en = time.monotonic()
                    estado = 2

                case 2:  # PEDIR_LOTE
                    _enviar(conexion, "lote (acciones separadas por ',', termina en /n). 1=saldo | 2 <cantidad>=ingresar | 3 <cantidad>=retirar: ")
                    entrada = _recibir(conexion)
                    if entrada is None: return
                    if not entrada: continue
                    
                    # Comprobamos la inactividad de la sesión (120 seg)
                    if time.monotonic() - autenticado_en > 720.0:
                        _enviar(conexion, "sesion expirada")
                        estado = 1
                        continue
                        
                    if len(entrada) > 256 or not re.fullmatch(r"[A-Za-z0-9 _.,;:/@#()-]+", entrada) or not entrada.endswith("/n"):
                        _enviar(conexion, "error 404 input no valido"); continue
                        
                    acciones_bruto = [p.strip() for p in entrada[:-2].split(",")]
                    if any(not p for p in acciones_bruto) or len(acciones_bruto) > 3:
                        _enviar(conexion, "error 404 input no valido"); continue
                        
                    saldo_temp = float(datos_usuario.get("balance", 0.0))
                    acciones_validas, errores = [], []
                    
                    for a in acciones_bruto:
                        partes = a.split()
                        acc = partes[0]
                        if acc not in ("1", "2", "3") or (acc == "1" and len(partes) != 1) or (acc in ("2", "3") and len(partes) != 2):
                            errores.append("error 404 input no valido"); continue
                            
                        cant = 0.0
                        if acc in ("2", "3"):
                            try:
                                cant = float(partes[1].replace(",", "."))
                                if cant < 0: raise ValueError
                            except ValueError:
                                errores.append("error 404 input no valido"); continue
                                
                        if acc == "2":
                            saldo_temp += cant
                        elif acc == "3":
                            if cant > saldo_temp:
                                errores.append(f"accion {acc} no tienes suficiente dinero en tu cuenta"); continue
                            saldo_temp -= cant
                            
                        acciones_validas.append({"action": int(acc), "amount": cant})
                        
                    if errores:
                        _enviar(conexion, "\n".join(errores))
                    
                    if not acciones_validas:
                        continue
                        
                    pendiente["lote"] = acciones_validas
                    pendiente["saldo"] = saldo_temp
                    estado = 3

                case 3:  # CONFIRMAR_LOTE
                    _enviar(conexion, "confirmar? (si/no): ")
                    entrada = _recibir(conexion)
                    if entrada is None: return
                    if not entrada: continue

                    # Comprobamos la inactividad de la sesión (120 seg)
                    if time.monotonic() - autenticado_en > 120.0:
                        _enviar(conexion, "sesion expirada")
                        estado = 1
                        continue
                    
                    if entrada.lower() in ("si", "s", "yes", "y"):
                        datos_usuario["balance"] = pendiente["saldo"]
                        _actualizar_bd(datos_usuario["username"], pendiente["saldo"], pendiente["lote"])
                        _enviar(conexion, f"acciones realizadas ({len(pendiente['lote'])}). balance={pendiente['saldo']}")
                    else:
                        _enviar(conexion, "usted ha denegado las acciones")
                        
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
            manejar_cliente(conexion, direccion)

if __name__ == "__main__":
    iniciar_servidor()