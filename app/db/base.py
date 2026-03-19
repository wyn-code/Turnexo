from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from decouple import config

DATABASE_URL = config('DB')

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("Conexión a PostgreSQL exitosa")
except Exception as e:
    print("Error de conexión:", e)
