from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base


class Metodo_Pago(Base):
    __tablename__ = "metodo_pago"

    id_metd = Column(Integer, primary_key=True, index=True)
    nombre_metd = Column(String(30), nullable=False)
    created_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
