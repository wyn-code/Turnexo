from fastapi import FastAPI

from app.routers import usuario, turno_router
from app.db.base import engine, text


app = FastAPI(title="Turnexo")


@app.get("/", summary="Healthcheck")
def root():
    return {"mensaje": "API Turnexo funcionando"}


@app.get("/db-test", summary="Prueba conexión DB")
def test_db():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 'conexion OK con postgres'"))
        return {"resultado": result.scalar()}


# Incluir routers
app.include_router(usuario.router, prefix="/api")
app.include_router(turno_router.router, prefix="/api")
