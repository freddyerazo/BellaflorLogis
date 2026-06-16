from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class BoxTypeCreate(BaseModel):
    box_code: str
    box_name: Optional[str] = None
    length_cm: Decimal
    width_cm: Decimal
    height_cm: Decimal
    cube_ft3: Optional[Decimal] = None
    reference_weight_kg: Optional[Decimal] = None


class BoxTypeUpdate(BaseModel):
    box_code: Optional[str] = None
    box_name: Optional[str] = None
    length_cm: Optional[Decimal] = None
    width_cm: Optional[Decimal] = None
    height_cm: Optional[Decimal] = None
    cube_ft3: Optional[Decimal] = None
    reference_weight_kg: Optional[Decimal] = None
    active: Optional[bool] = None
