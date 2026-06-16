from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI(
    title="BLIS API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
