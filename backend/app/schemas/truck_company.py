from typing import Optional

from pydantic import BaseModel


class TruckCompanyCreate(BaseModel):
    carrier_name: str
    sub_carrier_name: Optional[str] = None
    country: Optional[str] = None
    id_logistic_carrier: str


class TruckCompanyUpdate(BaseModel):
    carrier_name: Optional[str] = None
    sub_carrier_name: Optional[str] = None
    country: Optional[str] = None
    id_logistic_carrier: Optional[str] = None
    active: Optional[bool] = None
