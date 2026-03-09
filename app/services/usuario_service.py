from sqlalchemy.orm import Session
from app.models.usuario import Usuario
from app.schemas.usuario_schema import UsuarioCreate, UsuarioUpdate


def ver_usuarios(db: Session):
    return db.query(Usuario).all()


def ver_usuario_por_id(db: Session, usuario_id: int):
    return db.query(Usuario).filter(Usuario.id_us == usuario_id).first()


def crear_usuario(db: Session, usuario: UsuarioCreate):
    nuevo_usuario = Usuario(
        usuario_us=usuario.usuario_us,
        email_us=usuario.email_us,
        contrasena_us=usuario.contrasena_us
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario


def actualizar_usuario(db: Session, usuario_id: int, datos: UsuarioUpdate):
    usuario_db = db.query(Usuario).filter(Usuario.id_us == usuario_id).first()

    if not usuario_db:
        return None

    if datos.usuario_us is not None:
        usuario_db.usuario_us = datos.usuario_us

    if datos.email_us is not None:
        usuario_db.email_us = datos.email_us

    if datos.contrasena_us is not None:
        usuario_db.contrasena_us = datos.contrasena_us

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