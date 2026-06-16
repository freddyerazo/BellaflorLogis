from typing import Optional

from pydantic import BaseModel


class AirlineCreate(BaseModel):
    airline_code: str
    airline_name: str


class AirlineUpdate(BaseModel):
    airline_code: Optional[str] = None
    airline_name: Optional[str] = None
    active: Optional[bool] = None
