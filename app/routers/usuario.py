from typing import List

from fastapi import APIRouter

from app.schemas.usuario import Usuario

router = APIRouter()


@router.get("/usuarios", response_model=List[Usuario])
def obtener_usuarios():
    return [Usuario(nombre="Bruno", edad=22)]