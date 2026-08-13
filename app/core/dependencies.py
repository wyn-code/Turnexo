from collections.abc import Generator
from fastapi import HTTPException, status
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.models.negocio import Negocio

from app.services import plan_service

from app.core.config import ALGORITHM, SECRET_KEY
from app.db.database import SessionLocal
from app.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    usuario = db.query(Usuario).filter(
        Usuario.id_us == int(user_id)
    ).first()

    if usuario is None:
        raise credentials_exception

    if not usuario.estado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tu cuenta está desactivada. Contactá al administrador.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return usuario


def get_current_negocio(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Negocio:
    negocio = db.query(Negocio).filter(
        Negocio.usuario_id == current_user.id_us
    ).first()

    if negocio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no tiene un negocio registrado",
        )

    return negocio


def require_feature(feature_key: str):
    def dependency(
        negocio: Negocio = Depends(get_current_negocio),
        db: Session = Depends(get_db),
    ):
        if not plan_service.negocio_tiene_funcion(negocio.id_negocio, feature_key, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tu plan actual no incluye acceso a esta función. Actualizá al plan VIP para habilitarla.",
            )
        return negocio

    return dependency


def require_role(rol: str):
    def dependency(
        current_user: Usuario = Depends(get_current_user),
    ) -> Usuario:
        if current_user.role != rol:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permisos para realizar esta acción",
            )
        return current_user

    return dependency


def current_user_or_admin(
    usuario_id: int,
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    if current_user.role != "admin" and current_user.id_us != usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permisos para realizar esta acción",
        )
    return current_user