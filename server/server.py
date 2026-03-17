from __future__ import annotations

import json
from datetime import datetime
import re
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


DB_PATH = Path(__file__).with_name("clients_db.json")
SESSION_TTL_SECONDS = 120.0


class States:
    ASK_USERNAME = 0
    ASK_PASSWORD = 1
    ASK_BATCH = 2
    CONFIRM_BATCH = 3
    CLOSED = 99


@dataclass
class Session:
    state: int = States.ASK_USERNAME
    username: str = ""
    password: str = ""
    public_key: str = ""
    balance: float = 0.0
    batches_done: list[Any] = None  # type: ignore[assignment]
    _pending_username: str = ""
    _pending_batch_raw: str = ""
    _pending_valid_actions: list[dict[str, Any]] = None  # type: ignore[assignment]
    _pending_new_balance: float = 0.0
    authenticated_at: float = 0.0

    def __post_init__(self) -> None:
        if self.batches_done is None:
            self.batches_done = []
        if self._pending_valid_actions is None:
            self._pending_valid_actions = []


def _load_db() -> dict[str, Any]:
    with DB_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_db(db: dict[str, Any]) -> None:
    with DB_PATH.open("w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def _find_client(db: dict[str, Any], username: str) -> Optional[dict[str, Any]]:
    clients = db.get("clients", [])
    if not isinstance(clients, list):
        return None
    for c in clients:
        if isinstance(c, dict) and c.get("username") == username:
            return c
    return None


def update_client_balance(username: str, new_balance: float) -> bool:
    """
    Persiste el balance actualizado en clients_db.json.
    Llamar solo cuando el cliente confirme una acción.
    """
    db = _load_db()
    c = _find_client(db, username)
    if c is None:
        return False
    c["balance"] = float(new_balance)
    _save_db(db)
    return True


def _reset_pending_batch(session: Session) -> None:
    session._pending_batch_raw = ""
    session._pending_valid_actions = []
    session._pending_new_balance = 0.0


def _format_actions_as_batch(actions: list[dict[str, Any]]) -> str:
    """
    Convierte acciones válidas a texto tipo: "1,2 300,3 50"
    """
    parts: list[str] = []
    for a in actions:
        action = int(a.get("action", 0))
        amount = float(a.get("amount", 0.0))
        if action == 1:
            parts.append("1")
        elif action in (2, 3):
            # Evitamos notación científica y .0 innecesario
            amount_str = str(int(amount)) if float(amount).is_integer() else str(amount)
            parts.append(f"{action} {amount_str}")
    return ",".join(parts)


def append_client_batch_done(
    username: str,
    actions_performed: list[dict[str, Any]],
) -> bool:
    """
    Guarda el lote realizado en clients_db.json (campo batches_done) con:
      - batch (solo acciones correctas ejecutadas)
      - username
      - fecha/hora
    """
    db = _load_db()
    c = _find_client(db, username)
    if c is None:
        return False
    batches = c.get("batches_done", [])
    if not isinstance(batches, list):
        batches = []
    batches.append(
        {
            "batch": _format_actions_as_batch(actions_performed),
            "username": username,
            "datetime": datetime.now().isoformat(timespec="seconds"),
        }
    )
    c["batches_done"] = batches
    _save_db(db)
    return True


def _send(conn: socket.socket, text: str) -> None:
    # El cliente hace recv() bloqueante; si enviamos "" no llega nada y se queda esperando.
    # Para "mensajes vacíos" mandamos al menos un salto de línea.
    payload = text if text != "" else "\n"
    conn.sendall(payload.encode("utf-8"))


def _recv_message(conn: socket.socket) -> Optional[str]:
    """
    Recibe un mensaje (el cliente no manda '\\n').
    Devuelve None si el cliente cierra la conexión.
    """
    try:
        data = conn.recv(4096)
    except socket.timeout:
        return ""
    if not data:
        return None
    return data.decode("utf-8", errors="replace").strip()


def is_session_expired(session: Session) -> bool:
    if session.authenticated_at <= 0:
        return False
    return (time.monotonic() - session.authenticated_at) > SESSION_TTL_SECONDS


def validate_auth_input(conn: socket.socket, value: str, *, field: str) -> str:
    """
    Validación para inputs de autenticación (usuario/contraseña).
    Devuelve "" si es válido; si no, envía error al cliente y devuelve el texto de error.
    """
    v = (value or "").strip()
    if v == "":
        msg = "error 404 input no valido"
        _send(conn, msg)
        return msg
    if len(v) > 64:
        msg = "error 404 input no valido"
        _send(conn, msg)
        return msg
    if any(ch.isspace() for ch in v):
        msg = "error 404 input no valido"
        _send(conn, msg)
        return msg

    if field == "username":
        # Restrictivo pero simple: letras, números, guion bajo y guion.
        if not re.fullmatch(r"[A-Za-z0-9_-]+", v):
            msg = "error 404 input no valido"
            _send(conn, msg)
            return msg

    return ""


def validate_balance_input(conn: socket.socket, value: str) -> tuple[str, Optional[float]]:
    """
    Validación para inputs de balance/cantidad.
    Devuelve ("", float) si es válido; si no, envía error al cliente y devuelve (error, None).
    """
    v = (value or "").strip().replace(",", ".")
    try:
        amount = float(v)
    except ValueError:
        msg = "error 404 input no valido"
        _send(conn, msg)
        return msg, None

    if not (amount >= 0.0):
        msg = "error 404 input no valido"
        _send(conn, msg)
        return msg, None

    return "", amount


def validate_batch_input(conn: socket.socket, value: str) -> str:
    """
    Validación más restrictiva para el input de 'batch'.
    Por ahora solo comprueba formato básico; se endurecerá cuando definamos el formato exacto.
    Devuelve "" si es válido; si no, envía error al cliente y devuelve el texto de error.
    """
    v = (value or "").strip()
    if v == "":
        msg = "error 404 input no valido"
        _send(conn, msg)
        return msg
    if len(v) > 256:
        msg = "error 404 input no valido"
        _send(conn, msg)
        return msg
    # Permitimos solo caracteres “seguros” y separadores habituales.
    if not re.fullmatch(r"[A-Za-z0-9 _.,;:/@#()-]+", v):
        msg = "error 404 input no valido"
        _send(conn, msg)
        return msg
    return ""


def parse_lot(value: str) -> tuple[str, Optional[list[str]]]:
    """
    El cliente envía un lote terminado en "/n" (literal).
    Las acciones van separadas por comas, máximo 3 acciones por lote.

    Ejemplos:
      - "1/n"
      - "2 300/n"
      - "1,2 300,3 50/n"
    """
    raw = (value or "").strip()
    if not raw.endswith("/n"):
        return "error 404 input no valido", None
    raw = raw[: -len("/n")].strip()
    if raw == "":
        return "error 404 input no valido", None

    parts = [p.strip() for p in raw.split(",")]
    if any(p == "" for p in parts):
        return "error 404 input no valido", None
    if len(parts) > 3:
        return "error 404 input no valido", None
    return "", parts


def parse_batch(value: str) -> tuple[str, Optional[int], Optional[str]]:
    """
    Parsea el input del cliente para lote/acción.
    Formatos esperados (secuencial):
      - "1"
      - "2 <cantidad>"
      - "3 <cantidad>"
    Devuelve: (error, action, amount_str)
    """
    raw = (value or "").strip()
    parts = raw.split()
    if len(parts) == 0:
        return "error 404 input no valido", None, None
    if parts[0] not in {"1", "2", "3"}:
        return "error 404 input no valido", None, None

    action = int(parts[0])
    if action == 1:
        if len(parts) != 1:
            return "error 404 input no valido", None, None
        return "", action, None

    # action 2 o 3
    if len(parts) != 2:
        return "error 404 input no valido", None, None
    return "", action, parts[1]


def validate_batch_semantics(
    conn: socket.socket,
    current_balance: float,
    action: int,
    amount: Optional[float],
) -> tuple[str, float]:
    """
    Validación lógica del lote:
      1 = consulta saldo
      2 = ingresar cantidad  (balance + amount)
      3 = retirar cantidad   (balance - amount, sin quedar negativo)
    Devuelve (error, new_balance). Si hay error, envía al cliente y new_balance será session.balance.
    """
    if action == 1:
        return "", current_balance

    if amount is None:
        msg = "error 404 input no valido"
        _send(conn, msg)
        return msg, current_balance

    if action == 2:
        return "", current_balance + amount

    if action == 3:
        if amount > current_balance:
            msg = f"accion {action} no tienes suficiente dinero en tu cuenta"
            _send(conn, msg)
            return msg, current_balance
        return "", current_balance - amount

    msg = "error 404 input no valido"
    _send(conn, msg)
    return msg, current_balance


def handle_client(conn: socket.socket, addr: tuple[str, int]) -> None:
    session = Session()
    # Permite comprobar el TTL aunque estemos esperando input del cliente.
    conn.settimeout(1.0)

    while session.state != States.CLOSED:
        # TTL: si han pasado 2 minutos desde autenticación, volver a pedir contraseña.
        if session.state in {States.ASK_BATCH, States.CONFIRM_BATCH} and is_session_expired(session):
            _send(conn, "sesion expirada")
            session.password = ""
            _reset_pending_batch(session)
            session._pending_username = session.username
            session.state = States.ASK_PASSWORD
            continue

        match session.state:
            case States.ASK_USERNAME:
                _send(conn, "introduzca su usuario: ")
                raw = _recv_message(conn)
                if raw is None:
                    session.state = States.CLOSED
                    continue

                username = raw.strip()
                if validate_auth_input(conn, username, field="username") != "":
                    session.state = States.ASK_USERNAME
                    continue

                db = _load_db()
                client = _find_client(db, username)
                if client is None:
                    _send(conn, "usuario no existe")
                    session.state = States.ASK_USERNAME
                    continue

                session._pending_username = username
                session.state = States.ASK_PASSWORD

            case States.ASK_PASSWORD:
                _send(conn, "introduzca su contraseña: ")
                raw = _recv_message(conn)
                if raw is None:
                    session.state = States.CLOSED
                    continue
                if raw == "":
                    continue

                password = raw.strip()
                if validate_auth_input(conn, password, field="password") != "":
                    session._pending_username = ""
                    session.state = States.ASK_USERNAME
                    continue

                db = _load_db()
                client = _find_client(db, session._pending_username)
                if client is None:
                    _send(conn, "usuario no existe")
                    session._pending_username = ""
                    session.state = States.ASK_USERNAME
                    continue

                if client.get("password") != password:
                    _send(conn, "contraseña incorrecta")
                    session._pending_username = ""
                    session.state = States.ASK_USERNAME
                    continue

                # Cargamos la información del usuario en variables de sesión
                session.username = str(client.get("username", ""))
                session.password = str(client.get("password", ""))
                session.public_key = str(client.get("public_key", ""))
                session.balance = float(client.get("balance", 0.0))
                session.batches_done = list(client.get("batches_done", []))
                session._pending_username = ""
                session.authenticated_at = time.monotonic()

                session.state = States.ASK_BATCH

            case States.ASK_BATCH:
                # Cada vez que (re)entramos en ASK_BATCH, limpiamos pendientes del batch anterior
                _reset_pending_batch(session)
                _send(
                    conn,
                    "lote (acciones separadas por ',', termina en /n). "
                    "1=saldo | 2 <cantidad>=ingresar | 3 <cantidad>=retirar: ",
                )
                raw = _recv_message(conn)
                if raw is None:
                    session.state = States.CLOSED
                    continue
                if raw == "":
                    continue

                if validate_batch_input(conn, raw) != "":
                    session.state = States.ASK_BATCH
                    continue

                lerr, actions = parse_lot(raw)
                if lerr != "" or actions is None:
                    _send(conn, lerr if lerr != "" else "error 404 input no valido")
                    session.state = States.ASK_BATCH
                    continue

                # Primero: parsear y comprobar cada acción; construimos lista de válidas.
                errors: list[str] = []
                valid_actions: list[dict[str, Any]] = []
                temp_balance = float(session.balance)

                for a in actions:
                    perr, action, amount_str = parse_batch(a)
                    if perr != "" or action is None:
                        errors.append("error 404 input no valido")
                        continue

                    amount: Optional[float] = None
                    if amount_str is not None:
                        berr, parsed = validate_balance_input(conn, amount_str)
                        if berr != "" or parsed is None:
                            errors.append("error 404 input no valido")
                            continue
                        amount = parsed

                    # Validación lógica usando balance temporal (acciones en orden)
                    serr, new_balance = validate_batch_semantics(conn, temp_balance, action, amount)
                    if serr != "":
                        errors.append(serr)
                        continue

                    valid_actions.append(
                        {
                            "action": int(action),
                            "amount": float(amount or 0.0),
                            "balance_after": float(new_balance),
                        }
                    )
                    temp_balance = float(new_balance)

                # Enviar un solo mensaje con errores (si los hay), para mantener el patrón secuencial.
                if errors:
                    _send(conn, "\n".join(errors))

                if not valid_actions:
                    # Si no hay ninguna acción válida, volvemos a pedir el lote.
                    session.state = States.ASK_BATCH
                    continue

                session._pending_batch_raw = raw
                session._pending_valid_actions = valid_actions
                session._pending_new_balance = float(temp_balance)
                session.state = States.CONFIRM_BATCH

            case States.CONFIRM_BATCH:
                _send(conn, "confirmar? (si/no): ")
                raw = _recv_message(conn)
                if raw is None:
                    session.state = States.CLOSED
                    continue
                if raw == "":
                    continue

                ans = raw.strip().lower()
                if ans in {"si", "s", "yes", "y"}:
                    # Aplicar y persistir balance solo al confirmar
                    session.balance = session._pending_new_balance
                    update_client_balance(session.username, session.balance)
                    append_client_batch_done(session.username, session._pending_valid_actions)

                    _send(
                        conn,
                        f"acciones realizadas ({len(session._pending_valid_actions)}). balance={session.balance}",
                    )
                else:
                    _send(conn, "usted ha denegado las acciones")

                _reset_pending_batch(session)
                session.state = States.ASK_BATCH

            case _:
                session.state = States.CLOSED

    try:
        conn.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    conn.close()


def run_server(host: str = "127.0.0.1", port: int = 5000) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen()
        while True:
            conn, addr = s.accept()
            # Versión simple: atiende 1 cliente por vez (fácil de depurar)
            handle_client(conn, addr)


if __name__ == "__main__":
    run_server(port=6345)
