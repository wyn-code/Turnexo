from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)

from app.schemas.usuario_schema import UsuarioResponse


# =====================================
# REGISTER
# =====================================

class RegisterRequest(BaseModel):
    usuario_us: str = Field(
        min_length=3,
        max_length=30,
    )

    email_us: EmailStr

    contrasena_us: str = Field(
        min_length=12,
        max_length=16,
    )


# =====================================
# LOGIN
# =====================================

class LoginRequest(BaseModel):
    email_us: str
    contrasena_us: str = Field(
        min_length=12,
        max_length=16,
    )


# =====================================
# VERIFY CREDENTIALS
# =====================================

class VerifyCredentialsResponse(BaseModel):
    requires_2fa: bool = True
    message: str


# =====================================
# VERIFY 2FA
# =====================================

class Verify2FARequest(BaseModel):
    email_us: EmailStr

    otp_code: str = Field(
        min_length=6,
        max_length=6,
    )

# =====================================
# TOKEN
# =====================================

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# =====================================
# AUTH RESPONSE
# =====================================

class AuthResponse(BaseModel):
    usuario: UsuarioResponse
    token: TokenResponse

    model_config = ConfigDict(
        from_attributes=True
    )


# =====================================
# GOOGLE LOGIN
# =====================================

class GoogleLoginRequest(BaseModel):
    id_token: str


# =====================================
# FORGOT PASSWORD
# =====================================

class ForgotPasswordRequest(BaseModel):
    email_us: EmailStr


# =====================================
# RESET PASSWORD
# =====================================

class ResetPasswordRequest(BaseModel):
    new_password: str = Field(
        min_length=12,
        max_length=16,
    )

    confirm_password: str = Field(
        min_length=12,
        max_length=16,
    )

    model_config = ConfigDict(
        from_attributes=True
    )

