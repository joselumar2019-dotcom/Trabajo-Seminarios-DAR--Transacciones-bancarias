from pydantic import BaseModel, Field
from typing import List, Optional

class IdentificacionRequest(BaseModel):
    username: str = Field(..., description="Nombre de usuario del cliente")

class AutenticacionRequest(BaseModel):
    password: str = Field(..., description="Contraseña del cliente")

class BatchRequest(BaseModel):
    instrucciones: str = Field(..., description="Cadena de acciones separadas por comas (ej: '1, 2 100')")

class ConfirmacionRequest(BaseModel):
    decision: str = Field(..., description="Decisión de confirmar ('si' o 'no')")

class ResponseMessage(BaseModel):
    mensaje: str
    session_id: Optional[str] = None
    resumen: Optional[str] = None
    saldo_final: Optional[float] = None
