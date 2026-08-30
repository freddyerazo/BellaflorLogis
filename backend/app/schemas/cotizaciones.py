from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class CotizacionCreate(BaseModel):
    """Una cotizacion guardada desde el wizard.

    `estado` es el objeto `state` completo de cotizaciones.js: se guarda tal
    cual para poder reabrir la cotizacion exactamente como quedo. El resto de
    campos son la cabecera y los totales ya calculados, que se desnormalizan
    para que el listado no tenga que abrir el JSON.
    """

    nombre: str = Field(min_length=1, max_length=200)
    creado_por: Optional[str] = Field(default=None, max_length=120)

    ruta: Optional[str] = None
    aeropuerto_origen: Optional[str] = None
    aeropuerto_destino: Optional[str] = None
    incoterm: Optional[str] = None
    moneda: str = "USD"
    producto: Optional[str] = None

    cajas: Optional[int] = None
    total_stems: Optional[int] = None
    total_kg_real: Optional[Decimal] = None
    total_chargeable: Optional[Decimal] = None

    fob_usd: Optional[Decimal] = None
    s1_usd: Optional[Decimal] = None
    s2_usd: Optional[Decimal] = None
    s3_usd: Optional[Decimal] = None
    s4_usd: Optional[Decimal] = None
    s5_usd: Optional[Decimal] = None
    total_usd: Optional[Decimal] = None
    cost_per_stem: Optional[Decimal] = None
    cost_per_box: Optional[Decimal] = None

    estado: dict[str, Any]
