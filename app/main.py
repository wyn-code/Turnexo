from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.core.rate_limit import limiter
from app.db.database import engine
from app.routers.auth_router import router as auth_router
from app.routers.categoria_router import router as categoria_router
from app.routers.empleado_router import router as empleado_router
from app.routers.negocio_router import router as negocio_router
from app.routers.empleado_calendario_router import router as empleado_calendario_router
from app.routers.servicio_router import router as servicio_router
from app.routers.turno_router import router as turno_router
from app.routers.usuario_router import router as usuario_router
from app.routers.cliente_router import router as cliente_router
from app.routers.horarios_negocio_router import router as horarios_negocio_router
from app.routers.georef_router import router as georef_router
from app.routers.plan_router import router as plan_router
from app.routers.pago_router import router as pago_router
from app.routers.estadistica import router as estadistica

def create_app():
    app = FastAPI(title="Turnogo")

    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_exceeded_handler,
    )

    origins = [
    "http://localhost:5173",
    "https://www.turnogo.app",
    "https://turnogo.app",
]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", summary="Healthcheck")
    def root():
        return {"mensaje": "API Turnogo funcionando 🚀"}

    @app.get("/db-test", summary="Prueba conexión DB")
    def test_db():
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT 'conexion OK con postgres'")
            )
            return {"resultado": result.scalar()}

    app.include_router(usuario_router, prefix="/api", tags=["Usuarios"])
    app.include_router(auth_router, prefix="/api", tags=["Auth"])
    app.include_router(turno_router, prefix="/api", tags=["Turnos"])
    app.include_router(empleado_router, prefix="/api", tags=["Empleados"])
    app.include_router(servicio_router, prefix="/api", tags=["Servicios"])
    app.include_router(negocio_router, prefix="/api", tags=["Negocios"])
    app.include_router(empleado_calendario_router, prefix="/api", tags=["Empleados Calendario"])
    from app.routers.empleado_calendario_router import router_publico as empleado_calendario_router_publico
    app.include_router(empleado_calendario_router_publico, prefix="/api")
    app.include_router(categoria_router, prefix="/api", tags=["Categorias"])
    app.include_router(cliente_router, prefix="/api", tags=["Clientes"])
    app.include_router(horarios_negocio_router, prefix="/api", tags=["Horarios"])
    app.include_router(georef_router, prefix="/api", tags=["Georef"])
    app.include_router(plan_router, prefix="/api", tags=["Planes"])
    app.include_router(estadistica, prefix="/api", tags=["Estadistica"])
    app.include_router(pago_router, prefix="/api", tags=["Pagos"])
    return app


app = create_app()