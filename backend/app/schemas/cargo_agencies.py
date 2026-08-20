from typing import List, Optional

from pydantic import BaseModel


class CargoAgencyCreate(BaseModel):
    code: str
    name: str
    ocr_variants: Optional[List[str]] = []
    type: Optional[str] = "aerea"
    country: Optional[str] = "Ecuador"


class CargoAgencyUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    ocr_variants: Optional[List[str]] = None
    type: Optional[str] = None
    country: Optional[str] = None
    active: Optional[bool] = None
