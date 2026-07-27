from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets

from app.services.email_service import (
    send_verification_email,
)
from app.core.security import get_password_hash
from app.models.usuario import Usuario
from app.schemas.usuario_schema import UsuarioCreate, UsuarioUpdate
from sqlalchemy.orm import joinedload
from app.models.negocio import Negocio


def ver_usuarios(db: Session):
    return db.query(Usuario).all()


def ver_usuario_por_id(db: Session, usuario_id: int):
    return db.query(Usuario).filter(Usuario.id_us == usuario_id).first()


def _existe_usuario_us(db: Session, usuario_us: str, excluir_id: int | None = None):
    query = db.query(Usuario).filter(Usuario.usuario_us == usuario_us)
    if excluir_id is not None:
        query = query.filter(Usuario.id_us != excluir_id)
    return query.first() is not None


def _existe_email(db: Session, email_us: str, excluir_id: int | None = None):
    query = db.query(Usuario).filter(Usuario.email_us == email_us)
    if excluir_id is not None:
        query = query.filter(Usuario.id_us != excluir_id)
    return query.first() is not None


def crear_usuario(db: Session, usuario: UsuarioCreate):

    if _existe_usuario_us(db, usuario.usuario_us):
        raise HTTPException(
            status_code=409,
            detail="El nombre de usuario ya existe"
        )

    if _existe_email(db, usuario.email_us):
        raise HTTPException(
            status_code=409,
            detail="El email ya existe"
        )

    verification_token = secrets.token_urlsafe(32)

    nuevo_usuario = Usuario(
        usuario_us=usuario.usuario_us.strip(),
        email_us=usuario.email_us.strip(),
        contrasena_us=get_password_hash(
            usuario.contrasena_us
        ),

        email_verified=False,
        verification_token=verification_token,
        verification_token_expiration=(
            datetime.utcnow() + timedelta(hours=24)
        ),
    )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    send_verification_email(
        nuevo_usuario.email_us,
        verification_token,
    )

    return nuevo_usuario


def actualizar_usuario(db: Session, usuario_id: int, datos: UsuarioUpdate):
    usuario_db = db.query(Usuario).filter(Usuario.id_us == usuario_id).first()

    if not usuario_db:
        return None

    if datos.usuario_us is not None:
        if _existe_usuario_us(db, datos.usuario_us, excluir_id=usuario_id):
            raise HTTPException(status_code=409, detail="El nombre de usuario ya existe")
        usuario_db.usuario_us = datos.usuario_us.strip()

    if datos.email_us is not None:
        if _existe_email(db, datos.email_us, excluir_id=usuario_id):
            raise HTTPException(status_code=409, detail="El email ya existe")
        usuario_db.email_us = datos.email_us.strip()

    if datos.contrasena_us is not None:
        usuario_db.contrasena_us = get_password_hash(datos.contrasena_us)

    db.commit()
    db.refresh(usuario_db)
    return usuario_db


def borrar_usuario(db: Session, usuario_id: int):
    usuario_db = db.query(Usuario).filter(Usuario.id_us == usuario_id).first()

    if not usuario_db:
        return None

    db.delete(usuario_db)
    db.commit()
    return usuario_db


def ver_usuarios_admin(db: Session):
    usuarios = (
        db.query(Usuario)
        .options(joinedload(Usuario.negocios))
        .all()
    )

    return [
    {
        "id_us": u.id_us,
        "usuario_us": u.usuario_us,
        "email_us": u.email_us,
        "role_us": u.role,
        "estado": u.estado,
        "negocio": ", ".join(
            n.nombre for n in u.negocios
        ),
    }
    for u in usuarios
]

def cambiar_estado_usuario(
    db: Session,
    usuario_id: int,
    estado: bool
):
    usuario = (
        db.query(Usuario)
        .filter(Usuario.id_us == usuario_id)
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    usuario.estado = estado

    db.commit()
    db.refresh(usuario)

    return usuario

