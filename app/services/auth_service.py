from datetime import datetime, timedelta, timezone
import secrets
import re
from google.auth.exceptions import GoogleAuthError
from app.services.email_service import send_otp_email

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _check_estado(usuario: Usuario) -> None:
    if not usuario.estado:
        raise HTTPException(
            status_code=401,
            detail="Tu cuenta está desactivada. Contactá al administrador.",
        )


def _issue_token_or_send_otp(
    db: Session,
    usuario: Usuario,
) -> TokenResponse | None:
    """Devuelve un token si la 2FA fue verificada recientemente, o envía
    un OTP nuevo y devuelve None (el login debe continuar por /verify-2fa)."""
    if (
        usuario.last_2fa_verified_at is not None
        and usuario.last_2fa_verified_at
        >= _utcnow() - timedelta(hours=TWO_FACTOR_TOKEN_EXPIRE_HOURS)
    ):
        return TokenResponse(
            access_token=create_access_token(
                subject=usuario.id_us,
                expires_delta=timedelta(
                    hours=TWO_FACTOR_TOKEN_EXPIRE_HOURS
                ),
            )
        )

    otp = f"{secrets.randbelow(900000) + 100000}"

    usuario.otp_code = hash_otp(otp)
    usuario.otp_expires_at = (
        _utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES)
    )
    usuario.otp_attempts = 0

    db.commit()

    send_otp_email(
        usuario.email_us,
        otp,
    )

    return None

from app.services.email_service import (
    send_verification_email,
    send_reset_password_email,
    send_account_linked_email,
)
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    GOOGLE_CLIENT_ID,
    OTP_EXPIRE_MINUTES,
    TWO_FACTOR_TOKEN_EXPIRE_HOURS,
)
from app.core.security import (
    create_access_token,
    get_password_hash,
    hash_otp,
    verify_otp,
    verify_password,
)

from app.models.negocio import Negocio
from app.models.usuario import Usuario

from app.schemas.auth_schema import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    GoogleLoginResponse,
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


def login_user(
    db: Session,
    data: LoginRequest,
) -> tuple[Usuario, TokenResponse | None]:
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

    if not usuario.contrasena_us:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Esta cuenta no tiene contraseña configurada, "
                "iniciá sesión con Google o agregá una contraseña "
                "desde tu perfil"
            ),
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

    _check_estado(usuario)

    token = _issue_token_or_send_otp(db, usuario)

    return usuario, token


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

    if (
        usuario.contrasena_us
        and verify_password(
            new_password,
            usuario.contrasena_us,
        )
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

    if not usuario.contrasena_us:
        raise HTTPException(
            status_code=401,
            detail=(
                "Esta cuenta no tiene contraseña configurada, "
                "iniciá sesión con Google o agregá una contraseña "
                "desde tu perfil"
            ),
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

    _check_estado(usuario)

    token = _issue_token_or_send_otp(db, usuario)

    if token is not None:
        return {
            "success": True,
            "message": "Token emitido",
            "requires_2fa": False,
            "access_token": token.access_token,
        }

    return {
        "success": True,
        "requires_2fa": True,
        "message": "Código enviado al correo",
        "email": usuario.email_us,
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

    _check_estado(usuario)

    if (
        usuario.otp_expires_at is None
        or usuario.otp_expires_at < _utcnow()
    ):
        raise HTTPException(
            status_code=401,
            detail="El código de verificación ha expirado. Solicitá uno nuevo.",
        )

    if usuario.otp_attempts >= 5:
        raise HTTPException(
            status_code=401,
            detail="Superaste el límite de intentos. Solicitá un código nuevo.",
        )

    if not verify_otp(code, usuario.otp_code):
        usuario.otp_attempts = (usuario.otp_attempts or 0) + 1
        db.commit()
        raise HTTPException(
            status_code=401,
            detail="Código incorrecto",
        )

    usuario.otp_code = None
    usuario.otp_expires_at = None
    usuario.otp_attempts = 0
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


def resend_otp_code(
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
        raise HTTPException(
            status_code=401,
            detail="Usuario no encontrado",
        )

    if not usuario.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Debes verificar tu email antes de iniciar sesión",
        )

    _check_estado(usuario)

    token = _issue_token_or_send_otp(db, usuario)

    if token is not None:
        return {
            "success": True,
            "message": "Token emitido",
            "requires_2fa": False,
            "access_token": token.access_token,
        }

    return {
        "success": True,
        "requires_2fa": True,
        "message": "Código reenviado al correo",
        "email": usuario.email_us,
    }


def login_with_google(
    db: Session,
    id_token: str,
) -> tuple[Usuario, GoogleLoginResponse]:
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
    from google.auth.exceptions import GoogleAuthError

    try:
        payload = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except GoogleAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    google_id = payload.get("sub")
    email = payload.get("email")
    email_verified = payload.get("email_verified")

    if not google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo obtener el identificador de Google",
        )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo obtener el email de Google",
        )

    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El email de Google no está verificado",
        )

    def _issue_token(usuario: Usuario) -> str:
        return create_access_token(
            subject=usuario.id_us,
            expires_delta=timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            ),
        )

    usuario = (
        db.query(Usuario)
        .filter(Usuario.google_id == google_id)
        .first()
    )

    if usuario:
        _check_estado(usuario)
        return usuario, GoogleLoginResponse(
            access_token=_issue_token(usuario)
        )

    usuario = (
        db.query(Usuario)
        .filter(Usuario.email_us == email)
        .first()
    )

    if usuario:
        _check_estado(usuario)
        if usuario.google_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Esta cuenta ya está vinculada a otra cuenta "
                    "de Google. Iniciá sesión con esa cuenta o con "
                    "email y contraseña."
                ),
            )

        if not usuario.contrasena_us:
            usuario.email_verified = True
            usuario.google_id = google_id
            db.commit()
            db.refresh(usuario)
            return usuario, GoogleLoginResponse(
                access_token=_issue_token(usuario),
                account_linked=True,
            )

        if not usuario.email_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Existe una cuenta con este email que todavía "
                    "no verificó su email. Verificá tu email antes "
                    "de vincular tu cuenta de Google."
                ),
            )

        usuario.google_id = google_id
        db.commit()
        db.refresh(usuario)

        try:
            send_account_linked_email(usuario.email_us)
        except Exception:
            pass

        return usuario, GoogleLoginResponse(
            access_token=_issue_token(usuario),
            account_linked=True,
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

    usuario = Usuario(
        usuario_us=username,
        email_us=email,
        contrasena_us=None,
        email_verified=True,
        auth_provider="google",
        google_id=google_id,
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return usuario, GoogleLoginResponse(
        access_token=_issue_token(usuario),
        account_created=True,
    )


def set_password(
    db: Session,
    current_user: Usuario,
    new_password: str,
    current_password: str | None = None,
) -> dict:
    if not re.match(PASSWORD_REGEX, new_password):
        raise HTTPException(
            status_code=400,
            detail=(
                "La contraseña debe tener entre 12 y 16 caracteres, "
                "incluyendo mayúscula, minúscula, número "
                "y un carácter especial"
            ),
        )

    if current_user.contrasena_us:
        if not current_password:
            raise HTTPException(
                status_code=400,
                detail="Debés ingresar tu contraseña actual",
            )

        if not verify_password(
            current_password,
            current_user.contrasena_us,
        ):
            raise HTTPException(
                status_code=401,
                detail="La contraseña actual es incorrecta",
            )

        if verify_password(
            new_password,
            current_user.contrasena_us,
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "La nueva contraseña no puede ser "
                    "igual a la anterior"
                ),
            )

    current_user.contrasena_us = get_password_hash(new_password)
    current_user.auth_provider = "local"
    db.commit()
    db.refresh(current_user)

    return {
        "message": "Contraseña configurada correctamente"
    }
