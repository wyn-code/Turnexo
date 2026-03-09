from datetime import datetime
from typing import List

from fastapi import APIRouter

from app.schemas.usuario_schema import UsuarioResponse

router = APIRouter()


@router.get("/usuarios", response_model=List[UsuarioResponse])
def obtener_usuarios():
    usuarios = [
        {
            "id_us": 1,
            "usuario_us": "Bruno",
            "email_us": "bruno@gmail.com",
            "created_at": datetime.now(),
        }
    ]
    return usuarios
