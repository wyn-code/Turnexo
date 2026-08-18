from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_role
from app.models.usuario import Usuario
from app.schemas.categoria_schema import (
    CategoriaCreate,
    CategoriaResponse,
    CategoriaUpdate,
)
from app.services import categoria_service

router = APIRouter(prefix="/categorias", tags=["Categorias"])


@router.get("/", response_model=List[CategoriaResponse])
def listar(db: Session = Depends(get_db)):
    return categoria_service.listar_categorias(db)


@router.get("/{categoria_id}", response_model=CategoriaResponse)
def obtener(categoria_id: int, db: Session = Depends(get_db)):
    row = categoria_service.obtener_categoria_por_id(db, categoria_id)
    if not row:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")
    return row


@router.post("/", response_model=CategoriaResponse)
def crear(
    data: CategoriaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    try:
        return categoria_service.crear_categoria(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe una categoria con ese nombre",
        )


@router.put("/{categoria_id}", response_model=CategoriaResponse)
def actualizar(
    categoria_id: int,
    data: CategoriaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    try:
        row = categoria_service.actualizar_categoria(db, categoria_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe una categoria con ese nombre",
        )

    if not row:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")
    return row


@router.delete("/{categoria_id}")
def borrar(
    categoria_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    row = categoria_service.borrar_categoria(db, categoria_id)
    if not row:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")
    return {"mensaje": "Categoria eliminada"}
