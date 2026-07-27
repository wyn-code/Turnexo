from datetime import datetime, timedelta, timezone
import secrets
import re
import random
from google.auth.exceptions import GoogleAuthError
from app.services.email_service import send_otp_email

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

from app.services.email_service import (
    send_verification_email,
    send_reset_password_email,
)
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    GOOGLE_CLIENT_ID,
    TWO_FACTOR_TOKEN_EXPIRE_HOURS,
)
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)

from app.models.negocio import Negocio
from app.models.usuario import Usuario

from app.schemas.auth_schema import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)


PASSWORD_REGEX = (
    r"^(?=.*[a-z])"
    r"(?=.*[A-Z])"
    r"(?=.*\d)"
    r"(?=.*[@$!%*?&.#_-])"
    r"[A-Za-z\d@$!%*?&.#_-]{12,16}$"
)

def register_user(db: Session, data: RegisterRequest) -> Usuario:
    
    existing_user = (
        db.query(Usuario)
        .filter(
            or_(
                Usuario.email_us == data.email_us,
                Usuario.usuario_us == data.usuario_us,
            )
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email o nombre de usuario ya existe",
        )

    if not re.match(PASSWORD_REGEX, data.contrasena_us):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La contraseña debe tener entre 12 y 16 caracteres, "
                "incluyendo mayúscula, minúscula, número "
                "y un carácter especial"
            ),
        )

    verification_token = (
    secrets.token_urlsafe(32)
)

    usuario = Usuario(
        usuario_us=data.usuario_us.strip(),
        email_us=data.email_us.strip(),
        contrasena_us=get_password_hash(data.contrasena_us),

        email_verified=False,
        verification_token=verification_token,
        verification_token_expiration=(
            _utcnow() + timedelta(hours=24)
        ),
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    send_verification_email(
        usuario.email_us,
        verification_token,
    )

    return usuario


def login_user(db: Session, data: LoginRequest) -> tuple[Usuario, TokenResponse]:
    usuario = (
        db.query(Usuario)
        .filter(
            or_(
                Usuario.email_us == data.email_us,
                Usuario.usuario_us == data.email_us,
            )
        )
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas",
        )

    if not verify_password(
        data.contrasena_us,
        usuario.contrasena_us,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas",
        )
    
    if not usuario.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Debes verificar tu email antes de iniciar sesión",
    )

    token = create_access_token(
        subject=usuario.id_us,
        expires_delta=timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )

    return usuario, TokenResponse(
        access_token=token
    )


def build_me_response(db: Session, current_user: Usuario) -> dict:
    negocio = db.query(Negocio).filter(
        Negocio.usuario_id == current_user.id_us
    ).first()

    return {
        "id_us": current_user.id_us,
        "email_us": current_user.email_us,
        "usuario_us": current_user.usuario_us,
        "has_business": negocio is not None,
        "negocio_id": negocio.id_negocio if negocio else None,
        "negocio_slug": negocio.slug if negocio else None,
        "role": current_user.role,
    }


def forgot_password(
    db: Session,
    email: str,
):


    usuario = (
        db.query(Usuario)
        .filter(
            Usuario.email_us == email
        )
        .first()
    )


    if not usuario:
        return {
            "message": (
                "Si el email existe, se enviará un enlace"
            )
        }

    token = secrets.token_urlsafe(32)


    usuario.reset_token = token
    usuario.reset_token_expiration = (
        _utcnow() + timedelta(hours=24)
    )

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise

    try:
        send_reset_password_email(
            usuario.email_us,
            token,
        )
    except Exception as e:
        pass

    return {
        "message": (
            "Si el email existe, se enviará un enlace"
        )
    }


def reset_password(
    db: Session,
    token: str,
    new_password: str,
):
    usuario = (
        db.query(Usuario)
        .filter(
            Usuario.reset_token == token
        )
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=400,
            detail="Token inválido",
        )

    if (
        usuario.reset_token_expiration is None
        or usuario.reset_token_expiration
        < _utcnow()
    ):
        raise HTTPException(
            status_code=400,
            detail="Token expirado",
        )

    if not re.match(
        PASSWORD_REGEX,
        new_password,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "La contraseña debe tener "
                "entre 12 y 16 caracteres, "
                "incluyendo mayúscula, "
                "minúscula, número "
                "y un carácter especial"
            ),
        )

    if verify_password(
        new_password,
        usuario.contrasena_us,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "La nueva contraseña no puede ser "
                "igual a la anterior"
            ),
        )

    usuario.contrasena_us = (
        get_password_hash(new_password)
    )

    usuario.reset_token = None
    usuario.reset_token_expiration = None

    db.commit()

    return {
        "message": "Contraseña actualizada"
    }


def verify_email(
    db: Session,
    token: str,
):
    usuario = (
        db.query(Usuario)
        .filter(
            Usuario.verification_token == token
        )
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=400,
            detail="Token inválido",
        )

    if (
        usuario.verification_token_expiration is None
        or usuario.verification_token_expiration
        < _utcnow()
    ):
        raise HTTPException(
            status_code=400,
            detail="Token expirado",
        )

    usuario.email_verified = True
    usuario.verification_token = None
    usuario.verification_token_expiration = None

    db.commit()

    access_token = create_access_token(
        subject=usuario.id_us,
        expires_delta=timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    return {
        "message": "Email verificado correctamente",
        "access_token": access_token,
        "token_type": "bearer",
        "usuario_id": usuario.id_us,
    }

def verify_credentials(
    db: Session,
    data: LoginRequest,
):
    usuario = (
        db.query(Usuario)
        .filter(
            or_(
                Usuario.email_us == data.email_us,
                Usuario.usuario_us == data.email_us,
            )
        )
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas",
        )

    if not verify_password(
        data.contrasena_us,
        usuario.contrasena_us,
    ):
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas",
        )

    if not usuario.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Debes verificar tu email antes de iniciar sesión",
        )

    if (
        usuario.last_2fa_verified_at is not None
        and usuario.last_2fa_verified_at
        >= _utcnow() - timedelta(hours=TWO_FACTOR_TOKEN_EXPIRE_HOURS)
    ):
        access_token = create_access_token(
            subject=usuario.id_us,
            expires_delta=timedelta(
                hours=TWO_FACTOR_TOKEN_EXPIRE_HOURS
            ),
        )
        return {
            "success": True,
            "message": "Token emitido",
            "access_token": access_token,
        }

    otp = f"{random.randint(100000, 999999)}"

    usuario.otp_code = otp
    usuario.otp_expires_at = (
        _utcnow() + timedelta(minutes=10)
    )

    db.commit()

    send_otp_email(
        usuario.email_us,
        otp,
    )

    return {
        "success": True,
        "message": "Código enviado al correo",
    }

def verify_2fa(
    db: Session,
    email: str,
    code: str,
):
    usuario = (
        db.query(Usuario)
        .filter(
            Usuario.email_us == email
        )
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=401,
            detail="Usuario no encontrado",
        )

    if usuario.otp_code != code:
        raise HTTPException(
            status_code=401,
            detail="Código incorrecto",
        )

    if (
        usuario.otp_expires_at is None
        or usuario.otp_expires_at < _utcnow()
    ):
        raise HTTPException(
            status_code=401,
            detail="Código expirado",
        )

    usuario.otp_code = None
    usuario.otp_expires_at = None
    usuario.last_2fa_verified_at = _utcnow()

    db.commit()

    access_token = create_access_token(
        subject=usuario.id_us,
        expires_delta=timedelta(
            hours=TWO_FACTOR_TOKEN_EXPIRE_HOURS
        ),
    )

    return TokenResponse(
        access_token=access_token,
    )


def login_with_google(
    db: Session,
    id_token: str,
) -> tuple[Usuario, TokenResponse]:
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
    from google.auth.exceptions import GoogleAuthError

    print("=" * 60)
    print("GOOGLE_CLIENT_ID:", GOOGLE_CLIENT_ID)
    print("TOKEN (primeros 40):", id_token[:40])
    print("=" * 60)

    try:
        payload = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )

        print("GOOGLE PAYLOAD:", payload)

    except GoogleAuthError as e:
        print("GOOGLE AUTH ERROR:", repr(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    except Exception as e:
        print("GENERAL ERROR:", repr(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    email = payload.get("email")
    name = payload.get("name", "")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo obtener el email de Google",
        )

    usuario = (
        db.query(Usuario)
        .filter(Usuario.email_us == email)
        .first()
    )

    if usuario:
        if usuario.auth_provider != "google":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Este email ya está registrado con contraseña. "
                    "Iniciá sesión con email y contraseña."
                ),
            )

        token = create_access_token(
            subject=usuario.id_us,
            expires_delta=timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            ),
        )

        return usuario, TokenResponse(
            access_token=token,
        )

    username_base = email.split("@")[0]
    username = username_base
    counter = 1
    while (
        db.query(Usuario)
        .filter(Usuario.usuario_us == username)
        .first()
    ):
        username = f"{username_base}{counter}"
        counter += 1

    verification_token = secrets.token_urlsafe(32)

    usuario = Usuario(
        usuario_us=username,
        email_us=email,
        contrasena_us=None,
        email_verified=False,
        auth_provider="google",
        verification_token=verification_token,
        verification_token_expiration=(
            _utcnow() + timedelta(hours=24)
        ),
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    send_verification_email(
        usuario.email_us,
        verification_token,
    )

    return usuario, None
