from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.negocio import Negocio
from app.models.turnos import Turno
from app.models.usuario import Usuario
from app.schemas.cliente_schema import ClienteCreate, ClienteResponse
from app.services.cliente_service import (
    obtener_cliente_por_id,
    obtener_o_crear_cliente,
)

router = APIRouter(prefix="/clientes", tags=["Clientes"])


def _negocios_del_usuario(db: Session, user_id: int) -> list[int]:
    return [
        n.id_negocio
        for n in db.query(Negocio).filter(Negocio.usuario_id == user_id).all()
    ]


@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cliente = obtener_cliente_por_id(db, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if current_user.role == "admin":
        return cliente

    negocios = _negocios_del_usuario(db, current_user.id_us)
    tiene_turno = (
        db.query(Turno.id_turno)
        .filter(
            Turno.id_cliente == cliente_id,
            Turno.id_negocio.in_(negocios),
        )
        .first()
    )
    if not negocios or not tiene_turno:
        raise HTTPException(status_code=403, detail="No tienes permisos")
    return cliente


@router.get("/", response_model=list[ClienteResponse])
def listar(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.role == "admin":
        return db.query(Cliente).all()

    negocios = _negocios_del_usuario(db, current_user.id_us)
    if not negocios:
        return []

    return (
        db.query(Cliente)
        .join(Turno, Turno.id_cliente == Cliente.id_cliente)
        .filter(Turno.id_negocio.in_(negocios))
        .distinct()
        .all()
    )


@router.post("/get-or-create", response_model=ClienteResponse, status_code=200)
def get_or_create(datos: ClienteCreate, db: Session = Depends(get_db)):
    return obtener_o_crear_cliente(db, datos)