from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db, require_role
from app.models.usuario import Usuario
from app.schemas.negocio_schema import (
    NegocioResponse,
    NegocioListResponse,
    NegocioCompleteCreate,
    NegocioCompleteResponse,
    NegocioAdminResponse,
    NegocioUpdate,
    NegocioMapaResponse
)
from app.services import negocio_service

router = APIRouter(prefix="/negocios", tags=["Negocios"])


@router.post("/admin/rebuild-data")
def rebuild(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    return negocio_service.backfill_negocios(db)


@router.get("/mapa", response_model=list[NegocioMapaResponse])
def mapa(db: Session = Depends(get_db)):
    return negocio_service.obtener_negocios_mapa(db)


@router.get("/", response_model=list[NegocioListResponse])
def ver_negocios(db: Session = Depends(get_db)):
    return negocio_service.listar_negocios(db)


@router.get("/admin", response_model=list[NegocioAdminResponse])
def ver_negocios_admin(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    return negocio_service.listar_negocios_admin(db)

@router.get("/me", response_model=NegocioResponse)
def obtener_mi_negocio(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return negocio_service.obtener_negocio_por_usuario(
        db,
        current_user.id_us,
    )


@router.post("/", response_model=NegocioCompleteResponse, status_code=status.HTTP_201_CREATED)
def post_negocio(
    data: NegocioCompleteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if data.id_categoria is None:
        raise HTTPException(
            status_code=400, detail="id_categoria es obligatorio")

    data.usuario_id = current_user.id_us
    return negocio_service.crear_negocio_completo(db, data)


@router.post(
    "/complete",
    response_model=NegocioCompleteResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def post_negocio_completo(
    data: NegocioCompleteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return post_negocio(data, db, current_user)


@router.get("/slug/{slug}", response_model=NegocioResponse)
def ver_negocio_por_slug(slug: str, db: Session = Depends(get_db)):
    negocio = negocio_service.obtener_negocio_por_slug(db, slug)
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    return negocio


@router.get("/{negocio_id}", response_model=NegocioResponse)
def ver_negocio_por_id(
    negocio_id: int,
    db: Session = Depends(get_db)
):
    return negocio_service.obtener_negocio_publico_por_id(db, negocio_id)


@router.put("/{negocio_id}", response_model=NegocioResponse)
def update_negocio(
    negocio_id: int,
    data: NegocioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    return negocio_service.actualizar_negocio(
        db=db,
        negocio_id=negocio_id,
        data=data,
        current_user=current_user
    )


@router.delete("/{negocio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_negocio(
    negocio_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    negocio_service.eliminar_negocio(db, negocio_id, current_user)


@router.post("/backfill-coordenadas")
def ejecutar_backfill(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    negocio_service.backfill_negocios(db)

    return {
        "mensaje": "Coordenadas actualizadas"
    }
