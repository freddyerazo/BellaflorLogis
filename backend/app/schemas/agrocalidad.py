from uuid import UUID

from pydantic import BaseModel

# Areas de Agrocalidad: SA sanidad animal, SV sanidad vegetal,
# IAP/IAV/IAF insumos agricolas (pecuarios / veterinarios / fertilizantes).
# Bellaflor trabaja SV.
AREAS_VALIDAS = {"SA", "SV", "IAP", "IAV", "IAF"}

# Los movimientos validos viven en services/agrocalidad_api.MOVIMIENTOS: son
# los literales que espera el servicio, con tilde, y no conviene duplicarlos.


class AgrocalidadConsultaRequest(BaseModel):
    species_id: UUID
    country_id: UUID
    trade_type: str = "Exportación"
    area_code: str = "SV"
