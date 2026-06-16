from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class AirlineTariffCreate(BaseModel):
    airline_id: str
    origin_airport_id: str
    destination_airport_id: str
    cost_per_kg: Decimal
    minimum_charge: Optional[Decimal] = None
    currency_code: Optional[str] = "USD"
    valid_from: date
    valid_to: Optional[date] = None


class AirlineTariffUpdate(BaseModel):
    airline_id: Optional[str] = None
    origin_airport_id: Optional[str] = None
    destination_airport_id: Optional[str] = None
    cost_per_kg: Optional[Decimal] = None
    minimum_charge: Optional[Decimal] = None
    currency_code: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    active: Optional[bool] = None
