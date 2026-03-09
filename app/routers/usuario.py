from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.schemas.usuario_schema import UsuarioCreate, UsuarioUpdate, UsuarioResponse
from app.services.usuario_service import (
    crear_usuario,
    ver_usuarios,
    ver_usuario_por_id,
    actualizar_usuario,
    borrar_usuario
)

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[UsuarioResponse])
def get(db: Session = Depends(get_db)):
    return ver_usuarios(db)


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def get_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = ver_usuario_por_id(db, usuario_id)

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return usuario


@router.post("/", response_model=UsuarioResponse)
def create(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    return crear_usuario(db, usuario)


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def update(usuario_id: int, datos: UsuarioUpdate, db: Session = Depends(get_db)):
    usuario = actualizar_usuario(db, usuario_id, datos)

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return usuario


@router.delete("/{usuario_id}")
def delete(usuario_id: int, db: Session = Depends(get_db)):
    usuario = borrar_usuario(db, usuario_id)

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {"mensaje": "Usuario eliminado"}
