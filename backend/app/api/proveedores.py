"""
API del modulo Proveedores: catalogo de exportadores (proveedores) de
Bellaflor, en vivo desde el gateway movil de Logiztik Alliance.

No persiste nada en la base de BLIS: siempre consulta el API de Logiztik
(igual que Inventario LAG). Ver app/services/proveedores_client.py.
"""

from typing import Optional

from fastapi import APIRouter, Query

from app.services import proveedores_client as pc

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


@router.get("/health")
async def health():
    return {"status": "ok", "base_url": pc.LOGIZTIK_BASE_URL}


@router.get("/categorias")
async def categorias():
    """Categorias de mercancia disponibles para filtrar el catalogo."""
    return await pc.get_categorias()


@router.get("/exportadores")
async def exportadores(
    categoria: str = Query(..., description="IdCategoriaMercancia, p.ej. CME011 (Flores Frescas)"),
    exportador: Optional[str] = Query(default=None, description="Filtro por nombre de exportador"),
    producto: Optional[str] = Query(default=None, description="Filtro por nombre de producto"),
    pais: Optional[str] = Query(default=None, description="Filtro por idPais"),
):
    """Lista de proveedores (exportadores) para una categoria de mercancia."""
    return await pc.get_proveedores(
        id_categoria=categoria,
        busqueda_exportador=exportador,
        busqueda_producto=producto,
        id_pais=pais,
    )
