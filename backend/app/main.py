import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.db_test import router as db_router
from app.api.species import router as species_router
from app.api.varieties import router as varieties_router
from app.api.product_sizes import router as product_sizes_router
from app.api.box_types import router as box_router
from app.api.airports import router as airports_router
from app.api.countries import router as countries_router
from app.api.customers import router as customers_router
from app.api.airlines import router as airlines_router
from app.api.roles import router as roles_router
from app.api.profiles import router as profiles_router
from app.api.dashboard import router as dashboard_router
from app.api.cotizacion import router as cotizacion_router
from app.api.airline_tariffs import router as airline_tariffs_router
from app.api.cargo_agencies import router as cargo_agencies_router
from app.api.farms import router as farms_router
from app.api.dartis_import import router as dartis_router
from app.api.ingresos_locales import router as ingresos_locales_router
from app.api.agrocalidad import router as agrocalidad_router
from app.api.inventario_lag import router as inventario_lag_router
from app.api.torre_control import router as torre_control_router
from app.api.auditoria_etiquetas import router as auditoria_etiquetas_router
from app.api.truck_company import router as truck_company_router
from app.api.proveedores import router as proveedores_router
from app.api.armellini import router as armellini_router
from app.services import courier_reconciliation

scheduler = AsyncIOScheduler()

# Referencia al refresco inicial: sin guardarla, el recolector de basura
# puede cancelar la tarea antes de que termine.
_refresco_inicial: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Igual patron que el proyecto original: un refresco inicial y luego
    uno periodico cada REFRESH_SECONDS, protegidos por el mismo lock que
    usa el boton 'Actualizar ahora' (app/services/courier_reconciliation).

    El refresco inicial va en segundo plano y no con await: consulta UPS,
    FedEx y entregas locales, y tarda ~20s. Con await, el servidor no
    acepta conexiones hasta terminarlo — en Render (plan free) el servicio
    se duerme por inactividad, asi que ese costo se pagaba en cada
    despertar y podia agotar el timeout de arranque.
    """
    global _refresco_inicial
    _refresco_inicial = asyncio.create_task(courier_reconciliation.refrescar())
    scheduler.add_job(
        courier_reconciliation.refrescar, "interval",
        seconds=int(os.getenv("REFRESH_SECONDS", "300")),
    )
    scheduler.start()

    yield

    scheduler.shutdown(wait=False)
    if _refresco_inicial and not _refresco_inicial.done():
        _refresco_inicial.cancel()


app = FastAPI(
    title="BLIS API",
    version="1.0.0",
    lifespan=lifespan,
)

# El frontend se sirve desde este mismo origen, asi que no hace falta abrir
# CORS a terceros: con "*" cualquier web podia llamar a la API desde el
# navegador de un usuario. CORS_ORIGINS permite sumar origenes separados por
# coma (por ejemplo un frontend servido aparte durante desarrollo).
CORS_ORIGINS = [
    o.strip() for o in os.getenv(
        "CORS_ORIGINS",
        "https://blis-hxu1.onrender.com,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

_METODOS_ESCRITURA = ("POST", "PUT", "PATCH", "DELETE")

# El webhook de Telegram no pasa por la clave: Telegram no envia cabeceras
# propias y ya trae su secreto en X-Telegram-Bot-Api-Secret-Token.
_RUTAS_SIN_API_KEY = frozenset({"/api/auditoria-etiquetas/telegram/webhook"})


@app.middleware("http")
async def exigir_api_key_en_escrituras(request: Request, call_next):
    """Barrera minima mientras no haya login: sin BLIS_API_KEY configurada no
    exige nada (asi el deploy no rompe), y con ella toda escritura necesita la
    cabecera X-API-Key. No sustituye a la autenticacion: el frontend tiene que
    llevar la clave en su JavaScript, de modo que frena el acceso automatizado
    y anonimo, no a quien inspeccione la pagina."""
    clave = os.getenv("BLIS_API_KEY", "")
    if (
        clave
        and request.method in _METODOS_ESCRITURA
        and request.url.path not in _RUTAS_SIN_API_KEY
        and request.headers.get("X-API-Key") != clave
    ):
        return JSONResponse({"detail": "X-API-Key ausente o invalida"}, status_code=401)
    return await call_next(request)

app.include_router(health_router)
app.include_router(db_router)
app.include_router(species_router, prefix="/api")
app.include_router(varieties_router, prefix="/api")
app.include_router(product_sizes_router, prefix="/api")
app.include_router(box_router, prefix="/api")
app.include_router(airports_router, prefix="/api")
app.include_router(countries_router, prefix="/api")
app.include_router(customers_router, prefix="/api")
app.include_router(airlines_router, prefix="/api")
app.include_router(roles_router, prefix="/api")
app.include_router(profiles_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(cotizacion_router, prefix="/api")
app.include_router(airline_tariffs_router, prefix="/api")
app.include_router(cargo_agencies_router, prefix="/api")
app.include_router(farms_router, prefix="/api")
app.include_router(dartis_router, prefix="/api")
app.include_router(ingresos_locales_router, prefix="/api")
app.include_router(agrocalidad_router, prefix="/api")
app.include_router(inventario_lag_router, prefix="/api")
app.include_router(torre_control_router, prefix="/api")
app.include_router(auditoria_etiquetas_router, prefix="/api")
app.include_router(truck_company_router, prefix="/api")
app.include_router(proveedores_router, prefix="/api")
app.include_router(armellini_router, prefix="/api")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
