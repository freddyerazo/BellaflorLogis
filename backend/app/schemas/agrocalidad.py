from typing import Optional
from uuid import UUID

from pydantic import BaseModel

AREAS_VALIDAS = {"SA", "SV", "IAP", "IAV", "IAF"}
TIPOS_VALIDOS = {"Exportación", "Importación", "Tránsito", "Nacional"}


class AgrocalidadConsultaRequest(BaseModel):
    species_id: UUID
    country_id: UUID
    trade_type: str = "Exportación"
    area_code: str = "SV"


class AgrocalidadRequirement(BaseModel):
    id: UUID
    species_id: UUID
    country_id: UUID
    trade_type: str
    area_code: str
    matched_product_name: Optional[str] = None
    scientific_name: Optional[str] = None
    tariff_heading: Optional[str] = None
    agrocalidad_code: Optional[str] = None
    status: str
    requirements: Optional[str] = None
    queried_at: str


class AgrocalidadSolicitud(BaseModel):
    id: UUID
    status: str
    error_message: Optional[str] = None
    requirement: Optional[AgrocalidadRequirement] = None
