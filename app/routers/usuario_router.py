from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import (
    current_user_or_admin,
    get_current_user,
    require_role,
)
from app.db.session import get_db

from app.models.usuario import Usuario
from app.schemas.usuario_schema import UsuarioCreate, UsuarioUpdate, UsuarioResponse, UsuarioAdminResponse, EstadoUsuarioRequest
from app.services.usuario_service import (
    crear_usuario,
    ver_usuarios,
    ver_usuarios_admin,
    ver_usuario_por_id,
    actualizar_usuario,
    borrar_usuario,
    cambiar_estado_usuario,
)

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("/", response_model=list[UsuarioResponse])
def get(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    return ver_usuarios(db)

@router.get(
    "/admin",
    response_model=list[UsuarioAdminResponse]
)
def get_admin_users(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    return ver_usuarios_admin(db)


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def get_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(current_user_or_admin),
):
    usuario = ver_usuario_por_id(db, usuario_id)

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return usuario


@router.post("/", response_model=UsuarioResponse)
def create(
    usuario: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    return crear_usuario(db, usuario)


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def update(
    usuario_id: int,
    datos: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(current_user_or_admin),
):
    usuario = actualizar_usuario(db, usuario_id, datos)

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return usuario


@router.patch("/{usuario_id}/estado")
def cambiar_estado(
    usuario_id: int,
    data: EstadoUsuarioRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    return cambiar_estado_usuario(
        db,
        usuario_id,
        data.estado
    )

@router.delete("/{usuario_id}")
def delete(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    usuario = borrar_usuario(db, usuario_id)

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {"mensaje": "Usuario eliminado"}
