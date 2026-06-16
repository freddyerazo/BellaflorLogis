from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AirportCreate(BaseModel):
    iata_code: str
    airport_name: str
    city: Optional[str] = None
    country_id: Optional[UUID] = None


class AirportUpdate(BaseModel):
    iata_code: Optional[str] = None
    airport_name: Optional[str] = None
    city: Optional[str] = None
    country_id: Optional[UUID] = None
    active: Optional[bool] = None
