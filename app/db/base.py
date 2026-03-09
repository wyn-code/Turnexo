from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql+psycopg://postgres:123qwe@127.0.0.1:5432/Turnexo"

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
