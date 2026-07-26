from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.auth_service import (
    login_user,
    register_user,
    build_me_response,
    verify_email,
    forgot_password,
    reset_password,
    verify_credentials,
    verify_2fa,
    login_with_google,
)
from app.schemas.auth_schema import (
    AuthResponse,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    Verify2FARequest,
    TokenResponse,
)
from app.services.email_service import send_verification_email
from app.core.dependencies import get_current_user, get_db
from app.models.usuario import Usuario


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    usuario = register_user(
        db,
        payload,
    )

    return {
        "message":
            "Cuenta creada. Revisá tu email para verificarla.",
        "email": usuario.email_us,
    }


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    _, token = login_user(db, payload)
    return token

@router.post("/google")
def google_login(
    payload: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    usuario, token = login_with_google(db, payload.id_token)

    if token is None:
        return {
            "message":
                "Cuenta creada. Revisá tu email para verificarla.",
            "email": usuario.email_us,
        }

    return token

@router.get("/me")
def me(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_me_response(db, current_user)

@router.get("/test-email")
def test_email():
    response = send_verification_email(
        "brunoo6.massocco@gmail.com",
        "token-prueba",
    )

    return {
        "ok": True,
        "response": response,
    }

@router.post("/forgot-password")
def forgot_password_endpoint(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    return forgot_password(
        db,
        request.email_us,
    )


@router.post("/reset-password/{token}")
def reset_password_endpoint(
    token: str,
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Las contraseñas no coinciden",
        )

    return reset_password(
        db,
        token,
        request.new_password,
    )

@router.get("/verify-email/{token}")
def verify_email_endpoint(
    token: str,
    db: Session = Depends(get_db),
):
    return verify_email(
        db,
        token,
    )

@router.post("/verify-credentials")
def verify_credentials_endpoint(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    return verify_credentials(
        db,
        payload,
    )

@router.post(
    "/verify-2fa",
    response_model=TokenResponse,
)
def verify_2fa_endpoint(
    payload: Verify2FARequest,
    db: Session = Depends(get_db),
):
    return verify_2fa(
        db,
        payload.email_us,
        payload.otp_code,
    )