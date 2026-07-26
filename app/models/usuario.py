from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id_us = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    usuario_us = Column(
        String(50),
        nullable=False,
        unique=True,
    )

    email_us = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    contrasena_us = Column(
        String(255),
        nullable=True,
    )

    role = Column(
        String(20),
        default="duenio",
    )

    created_at = Column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    estado = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    # ==========================
    # EMAIL VERIFICATION
    # ==========================

    email_verified = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    verification_token = Column(
        String(255),
        nullable=True,
    )

    verification_token_expiration = Column(
        DateTime,
        nullable=True,
    )

    # ==========================
    # PASSWORD RESET
    # ==========================

    reset_token = Column(
        String(255),
        nullable=True,
    )

    reset_token_expiration = Column(
        DateTime,
        nullable=True,
    )

    # ==========================
    # TWO FACTOR AUTH
    # ==========================

    otp_code = Column(
        String(10),
        nullable=True,
    )

    otp_expires_at = Column(
        DateTime,
        nullable=True,
    )

    # ==========================
    # AUTH PROVIDER
    # ==========================

    auth_provider = Column(
        String(20),
        default="local",
        nullable=False,
    )

    negocios = relationship(
        "Negocio",
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )