from fastapi import FastAPI, HTTPException, status
from models import IdentificacionRequest, AutenticacionRequest, BatchRequest, ConfirmacionRequest, ResponseMessage
from session_manager import manager
import uvicorn

app = FastAPI(
    title="Banco REST API - Práctica 3",
    description="API REST para la gestión de operaciones bancarias, transicionada desde Java RMI.",
    version="1.0.0",
    contact={
        "name": "Pablo Serra García",
        "email": "pablo.serra@ejemplo.com",
        "name": "José Lis Martín Vera",
        "email": "joseluis.martin@ejemplo.com",
    }
)

@app.post("/sesiones",
          status_code=status.HTTP_201_CREATED,
          response_model=ResponseMessage,
          tags=["Sesiones"],
          summary="Paso 1: Identificación de usuario")
async def identificar(req: IdentificacionRequest):
    """
    Inicia el proceso de login identificando al usuario.
    Devuelve un `session_id` que debe usarse en las siguientes peticiones.
    """
    session_id = manager.crear_sesion(req.username)
    if not session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    return ResponseMessage(
        mensaje="Introduzca su contraseña:",
        session_id=session_id
    )

@app.put("/sesiones/{session_id}/auth",
         status_code=status.HTTP_200_OK,
         response_model=ResponseMessage,
         tags=["Sesiones"],
         summary="Paso 2: Autenticación con contraseña")
async def autenticar(session_id: str, req: AutenticacionRequest):
    """
    Actualiza el estado de la sesión validando la contraseña.
    Transición: sesión no autenticada → sesión autenticada.
    Se usa PUT porque modifica el estado de un recurso existente (/sesiones/{session_id}).
    """
    if manager.autenticar(session_id, req.password):
        return ResponseMessage(mensaje="Login correcto. Bienvenido.")

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña incorrecta o sesión no válida")

@app.post("/sesiones/{session_id}/lotes",
          status_code=status.HTTP_201_CREATED,
          response_model=ResponseMessage,
          tags=["Operaciones"],
          summary="Paso 3: Envío de lote de acciones")
async def procesar_lote(session_id: str, req: BatchRequest):
    """
    Envía una cadena de instrucciones para ser analizadas por el servidor.
    El lote queda pendiente de confirmación hasta que el cliente responda.
    """
    resultado = manager.procesar_lote(session_id, req.instrucciones)
    if "error" in resultado:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=resultado["error"])

    return ResponseMessage(
        mensaje=resultado["prompt"],
        resumen=resultado["resumen"]
    )

@app.post("/sesiones/{session_id}/lotes/confirmacion",
          status_code=status.HTTP_200_OK,
          response_model=ResponseMessage,
          tags=["Operaciones"],
          summary="Paso 4: Confirmación de operaciones")
async def confirmar(session_id: str, req: ConfirmacionRequest):
    """
    Confirma o cancela el lote de operaciones pendiente para la sesión indicada.
    """
    resultado = manager.confirmar(session_id, req.decision)
    if "error" in resultado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=resultado["error"])

    if resultado["status"] == "success":
        return ResponseMessage(
            mensaje="Operaciones confirmadas correctamente.",
            saldo_final=resultado["saldo_final"]
        )
    else:
        return ResponseMessage(mensaje="Lote cancelado.")

if __name__ == "__main__":
    # Escucha en todas las interfaces para permitir acceso distribuido
    uvicorn.run(app, host="0.0.0.0", port=8000)