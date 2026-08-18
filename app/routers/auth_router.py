from fastapi import APIRouter, Depends, HTTPException, Request
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
    resend_otp_code,
    login_with_google,
    set_password,
)
from app.schemas.auth_schema import (
    ForgotPasswordRequest,
    GoogleLoginRequest,
    GoogleLoginResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    ResendCodeRequest,
    SetPasswordRequest,
    Verify2FARequest,
    TokenResponse,
)
from app.services.email_service import send_verification_email
from app.core.dependencies import get_current_user, get_db
from app.core.rate_limit import limiter
from app.models.usuario import Usuario


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
@limiter.limit("5/minute")
def register(
    request: Request,
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


@router.post("/login")
@limiter.limit("15/minute")
def login(
    request: Request,
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    usuario, token = login_user(db, payload)

    if token is not None:
        return token

    return {
        "requires_2fa": True,
        "email": usuario.email_us,
    }

@router.post("/google", response_model=GoogleLoginResponse)
@limiter.limit("15/minute")
def google_login(
    request: Request,
    payload: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    _, token = login_with_google(db, payload.id_token)
    return token

@router.post("/set-password")
def set_password_endpoint(
    payload: SetPasswordRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Las contraseñas no coinciden",
        )

    return set_password(
        db,
        current_user,
        payload.new_password,
        payload.current_password,
    )

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
@limiter.limit("5/minute")
def forgot_password_endpoint(
    request: Request,
    forgot_password_payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    return forgot_password(
        db,
        forgot_password_payload.email_us,
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
@limiter.limit("15/minute")
def verify_credentials_endpoint(
    request: Request,
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
@limiter.limit("10/minute")
def verify_2fa_endpoint(
    request: Request,
    payload: Verify2FARequest,
    db: Session = Depends(get_db),
):
    return verify_2fa(
        db,
        payload.email_us,
        payload.otp_code,
    )

@router.post("/resend-code")
@limiter.limit("10/minute")
def resend_code_endpoint(
    request: Request,
    payload: ResendCodeRequest,
    db: Session = Depends(get_db),
):
    return resend_otp_code(
        db,
        payload.email_us,
    )