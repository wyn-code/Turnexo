import re
import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload
from app.models.localidad import Localidad
from app.models.provincia import Provincia
from app.models.negocio import Negocio
from app.models.usuario import Usuario
from app.models.servicio import Servicio
from app.models.empleado import Empleado
from app.models.categoria import Categoria
from app.models.negocio_imagen import NegocioImagen
from app.services.mapbox_service import obtener_coordenadas
from app.schemas.negocio_schema import NegocioCompleteCreate
from app.models.horarios_negocio import HorarioNegocio
from app.services.plan_service import negocio_tiene_funcion
from app.models.suscripcion import Suscripcion
from app.models.plan_feature import PlanFeature
from app.models.plan import Plan
from datetime import datetime



logger = logging.getLogger(__name__)

ALLOWED_FIELDS = {
    "nombre",
    "wsp",
    "telefono",
    "direccion",
    "ciudad",
    "ig_url",
    "logo",
    "descripcion",
    "activo",
    "id_categoria",
    "id_localidad",
    "id_provincia"
}


def obtener_negocios_mapa(db: Session):
    return (
        db.query(
            Negocio.id_negocio,
            Negocio.nombre,
            Negocio.latitud,
            Negocio.longitud,
        )
        .join(Suscripcion, Suscripcion.id_negocio == Negocio.id_negocio)
        .join(Plan, Plan.id_plan == Suscripcion.id_plan)
        .join(PlanFeature, PlanFeature.id_plan == Plan.id_plan)
        .filter(
            Negocio.latitud.isnot(None),
            Negocio.longitud.isnot(None),
            Negocio.activo == True,
            Suscripcion.estado == "activa",
            Suscripcion.fecha_fin >= datetime.now(),
            PlanFeature.feature_key == "mapa_ubicacion",
        )
        .all()
    )

def listar_negocios(db: Session):
    return db.query(Negocio).filter(
        Negocio.activo == True
    ).all()


def listar_negocios_admin(db: Session):
    negocios = (
        db.query(Negocio)
        .options(
            joinedload(Negocio.categoria),
            joinedload(Negocio.usuario),
        )
        .all()
    )

    return [
        {
            "id_negocio": n.id_negocio,
            "nombre": n.nombre,
            "wsp": n.wsp,
            "telefono": n.telefono,
            "direccion": n.direccion,
            "ciudad": n.ciudad,
            "ig_url": n.ig_url,
            "activo": n.activo,
            "slug": n.slug,
            "duenio": {
                "nombre": n.usuario.usuario_us,
                "email": n.usuario.email_us,
            },
        }
        for n in negocios
    ]


def obtener_negocio_por_id(db: Session, negocio_id: int):
    negocio = db.query(Negocio).options(
        joinedload(Negocio.categoria)
    ).filter(
        Negocio.id_negocio == negocio_id
    ).first()

    if not negocio:
        raise HTTPException(
            status_code=404,
            detail="Negocio no encontrado"
        )

    return negocio


def obtener_negocio_publico_por_id(db: Session, negocio_id: int):
    negocio = (
        db.query(Negocio)
        .options(
            joinedload(Negocio.categoria),
            selectinload(Negocio.horarios),
            selectinload(Negocio.imagenes),
        )
        .filter(
            Negocio.id_negocio == negocio_id,
            Negocio.activo == True
        )
        .first()
    )
    if not negocio:
        raise HTTPException(
            status_code=404,
            detail="Negocio no encontrado"
        )

    return negocio

def obtener_negocio_por_usuario(
    db: Session,
    usuario_id: int,
):
    negocio = (
        db.query(Negocio)
        .filter(Negocio.usuario_id == usuario_id)
        .first()
    )

    if not negocio:
        raise HTTPException(
            status_code=404,
            detail="El usuario no tiene un negocio",
        )

    return negocio


def obtener_negocio_por_slug(db: Session, slug: str):
    negocio = db.query(Negocio).options(
        joinedload(Negocio.categoria),
        selectinload(Negocio.horarios),
        selectinload(Negocio.imagenes),
    ).filter(
        Negocio.slug == slug,
        Negocio.activo == True
    ).first()
    if not negocio:
        raise HTTPException(
            status_code=404,
            detail="Negocio no encontrado"
        )

    return negocio


def generar_slug(nombre: str) -> str:
    slug = nombre.lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    return slug


def generar_slug_unico(db, nombre: str):
    base_slug = generar_slug(nombre)
    slug = base_slug
    contador = 1

    while db.query(Negocio).filter(Negocio.slug == slug).first():
        slug = f"{base_slug}-{contador}"
        contador += 1

    return slug


def crear_negocio_completo(db: Session, data: NegocioCompleteCreate):

    if not data.usuario_id:
        raise HTTPException(400, "usuario_id es obligatorio")

    usuario = db.query(Usuario).filter(
        Usuario.id_us == data.usuario_id).first()
    if not usuario:
        raise HTTPException(400, "Usuario no válido")

    if not data.id_categoria:
        raise HTTPException(400, "id_categoria es obligatorio")

    categoria = db.query(Categoria).filter(
        Categoria.id_categoria == data.id_categoria
    ).first()

    if not categoria:
        raise HTTPException(400, "Categoría no válida")

    localidad = None
    if data.id_localidad:
        localidad = db.query(Localidad).filter(
            Localidad.id_localidad == data.id_localidad
        ).first()
        if not localidad:
            raise HTTPException(400, f"Localidad no válida: {data.id_localidad}")

    provincia = None
    if data.id_provincia:
        provincia = db.query(Provincia).filter(
            Provincia.id_provincia == data.id_provincia
        ).first()
        if not provincia:
            raise HTTPException(400, f"Provincia no válida: {data.id_provincia}")

    # 🔥 GEOCODING MEJORADO
    latitud, longitud = None, None

    try:
        if data.direccion:
            coords = obtener_coordenadas(
                direccion=data.direccion,
                ciudad=localidad.nombre if localidad else None,
                provincia=provincia.nombre if provincia else None,
            )

            if coords:
                latitud, longitud = coords

    except Exception:
        logger.exception("Error obteniendo coordenadas desde Mapbox")

    slug = generar_slug_unico(db, data.nombre)

    nuevo_negocio = Negocio(
        usuario_id=data.usuario_id,
        nombre=data.nombre,
        wsp=data.wsp,
        telefono=data.telefono,
        direccion=data.direccion,
        ciudad=localidad.nombre if localidad else data.ciudad,
        id_localidad=data.id_localidad,
        id_provincia=data.id_provincia,
        ig_url=data.ig_url,
        logo=data.logo,
        descripcion=data.descripcion,
        activo=data.activo,
        id_categoria=data.id_categoria,
        slug=slug,
        latitud=latitud,
        longitud=longitud,
    )

    try:
        db.add(nuevo_negocio)
        db.flush()

        imagenes = [url.strip()
                    for url in (data.imagenes or []) if url and url.strip()]
        for index, url in enumerate(imagenes):
            db.add(NegocioImagen(
                id_negocio=nuevo_negocio.id_negocio,
                url=url,
                es_portada=index == 0,
                orden=index,
            ))

        # 🔥 SERVICIOS
        for servicio in data.servicios:
            db.add(Servicio(
                id_negocio=nuevo_negocio.id_negocio,
                **servicio.model_dump()
            ))

        # 🔥 EMPLEADOS
        for empleado in data.empleados:
            db.add(Empleado(
                id_negocio=nuevo_negocio.id_negocio,
                **empleado.model_dump()
            ))

        # 🔥 HORARIOS
        for horario in data.horarios:
            db.add(HorarioNegocio(
                id_negocio=nuevo_negocio.id_negocio,
                **horario.model_dump()
            ))

        db.commit()
        db.refresh(nuevo_negocio)

        return nuevo_negocio

    except Exception as e:
        db.rollback()
        logger.exception(f"Error creando negocio completo: {e}")

        raise HTTPException(500, "Error al crear el negocio")

 # 🔥 UPDATE NEGOCIO


def actualizar_negocio(db: Session, negocio_id: int, data, current_user: Usuario):

    negocio = (
        db.query(Negocio)
        .options(selectinload(Negocio.imagenes))
        .filter(Negocio.id_negocio == negocio_id)
        .first()
    )

    if not negocio:
        raise HTTPException(404)

    if negocio.usuario_id != current_user.id_us and current_user.role != "admin":
        raise HTTPException(403)

    update_data = data.model_dump(exclude_unset=True)
    imagenes = update_data.pop("imagenes", None)

    if "id_categoria" in update_data and update_data["id_categoria"] is not None:
        categoria = db.query(Categoria).filter(
            Categoria.id_categoria == update_data["id_categoria"]
        ).first()
        if not categoria:
            raise HTTPException(400, "Categoría no válida")

    old_direccion = negocio.direccion
    old_ciudad = negocio.ciudad

    for k, v in update_data.items():
        if k in ALLOWED_FIELDS:
            setattr(negocio, k, v)

    if imagenes is not None:
        # ── NUEVO: solo negocios VIP pueden subir imágenes personalizadas ──
        if not negocio_tiene_funcion(negocio.id_negocio, "imagenes_personalizadas", db):
            raise HTTPException(
                status_code=403,
                detail="Tu plan actual no incluye imágenes personalizadas. Actualizá al plan VIP.",
            )
        # ────────────────────────────────────────────────────────────────────
        urls = [url.strip() for url in imagenes if url and url.strip()]
        negocio.imagenes = [
            NegocioImagen(
                url=url,
                es_portada=index == 0,
                orden=index,
            )
            for index, url in enumerate(urls)
        ]

    if (
        negocio.direccion != old_direccion or
        negocio.ciudad != old_ciudad
    ):
        localidad = db.query(Localidad).filter(
            Localidad.id_localidad == negocio.id_localidad
        ).first()
        provincia = db.query(Provincia).filter(
            Provincia.id_provincia == negocio.id_provincia
        ).first()
        coords = obtener_coordenadas(
            direccion=negocio.direccion,
            ciudad=localidad.nombre if localidad else negocio.ciudad,
            provincia=provincia.nombre if provincia else None,
        )
        if coords:
            negocio.latitud, negocio.longitud = coords

    db.commit()
    db.refresh(negocio)
    return negocio


def eliminar_negocio(db: Session, negocio_id: int, current_user: Usuario):

    if current_user.role != "admin":
        raise HTTPException(403)

    negocio = db.query(Negocio).filter(
        Negocio.id_negocio == negocio_id
    ).first()

    if not negocio:
        raise HTTPException(404)

    negocio.activo = False

    db.commit()

#


def backfill_negocios(db: Session):
    negocios = db.query(Negocio).all()

    for n in negocios:
        updated = False

        # 1. Coordenadas
        if n.latitud is None or n.longitud is None:

            localidad = None
            provincia = None

            if n.id_localidad:
                localidad = db.query(Localidad).filter(
                    Localidad.id_localidad == n.id_localidad
                ).first()

            if localidad:
                provincia = db.query(Provincia).filter(
                    Provincia.id_provincia == localidad.id_provincia
                ).first()

            coords = obtener_coordenadas(
                direccion=n.direccion,
                ciudad=localidad.nombre if localidad else n.ciudad,
                provincia=provincia.nombre if provincia else None,
            )

            if coords:
                n.latitud, n.longitud = coords
                updated = True

        if updated:
            db.add(n)

    db.commit()