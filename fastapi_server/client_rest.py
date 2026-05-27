import requests
import sys

BASE_URL = "http://localhost:8000"

def main():
    print("--- Cliente Interactivo Banco REST ---")
    
    # 1. Identificación
    while True:
        username = input("Introduzca su usuario: ")
        try:
            resp = requests.post(f"{BASE_URL}/sesiones", json={"username": username})
            if resp.status_code == 201:
                data = resp.json()
                session_id = data["session_id"]
                print(f"\n[Srv] {data['mensaje']}")
                break
            else:
                print(f"[Err] {resp.json()['detail']}")
        except Exception as e:
            print(f"[Err] No se pudo conectar con el servidor: {e}")
            sys.exit(1)

    # 2. Autenticación
    while True:
        password = input("Contraseña: ")
        resp = requests.put(f"{BASE_URL}/sesiones/{session_id}/auth", json={"password": password})
        if resp.status_code == 200:
            print(f"\n[Srv] {resp.json()['mensaje']}")
            break
        else:
            print(f"[Err] {resp.json()['detail']}")

    # 3. Ciclo de Lotes
    while True:
        print("\nLote (1=saldo, 2 <cant>=ingresar, 3 <cant>=retirar, 4=salir)")
        entrada = input("Acciones: ")
        
        if entrada.strip() == "4":
            print("Sesión finalizada.")
            break
            
        # Enviar lote
        resp = requests.post(f"{BASE_URL}/sesiones/{session_id}/lotes", json={"instrucciones": entrada})
        if resp.status_code == 201:
            data = resp.json()
            print(f"\n{data['resumen']}")
            print(f"{data['mensaje']}")
            
            # Confirmar
            decision = input("> ")
            resp_conf = requests.post(f"{BASE_URL}/sesiones/{session_id}/lotes/confirmacion", json={"decision": decision})
            if resp_conf.status_code == 200:
                print(f"\n[Srv] {resp_conf.json()['mensaje']}")
                if "saldo_final" in resp_conf.json() and resp_conf.json()["saldo_final"] is not None:
                    print(f"Saldo actual: {resp_conf.json()['saldo_final']}€")
            else:
                print(f"[Err] {resp_conf.json()['detail']}")
        else:
            print(f"[Err] {resp.json()['detail']}")

if __name__ == "__main__":
    main()
