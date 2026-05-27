import json
import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

RUTA_BD = Path(__file__).parent.parent / "server" / "clients_db.json"
db_lock = threading.Lock()

class SessionManager:
    def __init__(self):
        self.sesiones: Dict[str, dict] = {}  # session_id -> {username, balance_temp, pending_ops, authenticated}
    
    def _cargar_bd(self) -> dict:
        with db_lock:
            if not RUTA_BD.exists(): 
                return {"clients": []}
            with RUTA_BD.open("r", encoding="utf-8") as archivo:
                return json.load(archivo)

    def _guardar_bd(self, bd: dict) -> None:
        with db_lock:
            with RUTA_BD.open("w", encoding="utf-8") as archivo:
                json.dump(bd, archivo, ensure_ascii=False, indent=2)

    def crear_sesion(self, username: str) -> str:
        bd = self._cargar_bd()
        cliente = next((c for c in bd.get("clients", []) if c.get("username") == username), None)
        if not cliente:
            return None
        
        session_id = str(uuid.uuid4())
        self.sesiones[session_id] = {
            "username": username,
            "authenticated": False,
            "balance_temp": 0.0,
            "pending_ops": [],
            "last_access": datetime.now()
        }
        return session_id

    def autenticar(self, session_id: str, password: str) -> bool:
        session = self.sesiones.get(session_id)
        if not session:
            return False
        
        bd = self._cargar_bd()
        cliente = next((c for c in bd.get("clients", []) if c.get("username") == session["username"]), None)
        
        if cliente and cliente.get("password") == password:
            session["authenticated"] = True
            session["balance_temp"] = float(cliente.get("balance", 0.0))
            return True
        return False

    def procesar_lote(self, session_id: str, instrucciones: str) -> dict:
        session = self.sesiones.get(session_id)
        if not session or not session["authenticated"]:
            return {"error": "Sesión no válida o no autenticada"}

        acciones_bruto = [p.strip() for p in instrucciones.split(",")]
        if any(not p for p in acciones_bruto) or len(acciones_bruto) > 3:
            return {"error": "Formato de lote inválido o demasiadas acciones (máx 3)"}

        saldo_temp = session["balance_temp"]
        acciones_validas = []
        resumen = ["--- Análisis del Lote ---"]

        for a in acciones_bruto:
            partes = a.split()
            acc = partes[0]
            
            try:
                if acc == "1":
                    resumen.append("[OK] Acción 1: Consulta de saldo.")
                    acciones_validas.append({"action": 1, "amount": 0.0})
                elif acc == "2":
                    cant = float(partes[1].replace(",", "."))
                    if cant < 0: raise ValueError
                    saldo_temp += cant
                    resumen.append(f"[OK] Acción 2: Ingresar {cant}€")
                    acciones_validas.append({"action": 2, "amount": cant})
                elif acc == "3":
                    cant = float(partes[1].replace(",", "."))
                    if cant < 0: raise ValueError
                    if cant > saldo_temp:
                        resumen.append(f"[X] Acción 3: Saldo insuficiente para retirar {cant}€")
                        continue
                    saldo_temp -= cant
                    resumen.append(f"[OK] Acción 3: Retirar {cant}€")
                    acciones_validas.append({"action": 3, "amount": cant})
                else:
                    resumen.append(f"[X] Acción {acc} no reconocida.")
            except (ValueError, IndexError):
                resumen.append(f"[X] Error de formato en acción: {a}")

        session["pending_ops"] = acciones_validas
        session["new_balance"] = saldo_temp
        
        return {
            "resumen": "\n".join(resumen),
            "prompt": "¿Confirmar acciones [OK]? (si/no)"
        }

    def confirmar(self, session_id: str, decision: str) -> dict:
        session = self.sesiones.get(session_id)
        if not session or not session["authenticated"]:
            return {"error": "Sesión no válida"}

        if decision.lower() in ("si", "s", "yes", "y"):
            bd = self._cargar_bd()
            username = session["username"]
            nuevo_saldo = session["new_balance"]
            acciones = session["pending_ops"]

            for cliente in bd.get("clients", []):
                if cliente.get("username") == username:
                    cliente["balance"] = nuevo_saldo
                    
                    # Registrar lote en historial
                    partes = []
                    for a in acciones:
                        acc, cant = a["action"], a["amount"]
                        if acc == 1: partes.append("1")
                        else:
                            cant_str = str(int(cant)) if float(cant).is_integer() else str(cant)
                            partes.append(f"{acc} {cant_str}")
                    
                    cliente.setdefault("batches_done", []).append({
                        "batch": ",".join(partes),
                        "datetime": datetime.now().isoformat(timespec="seconds")
                    })
                    break
            
            self._guardar_bd(bd)
            session["balance_temp"] = nuevo_saldo
            session["pending_ops"] = []
            return {"status": "success", "saldo_final": nuevo_saldo}
        
        session["pending_ops"] = []
        return {"status": "cancelled"}

# Instancia única para el servidor
manager = SessionManager()
