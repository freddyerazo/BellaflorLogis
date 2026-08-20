from typing import List, Optional

from pydantic import BaseModel


class FarmCreate(BaseModel):
    code: str
    name: str
    ocr_variants: Optional[List[str]] = []
    dartis_postcosecha: Optional[str] = None


class FarmUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    ocr_variants: Optional[List[str]] = None
    dartis_postcosecha: Optional[str] = None
    active: Optional[bool] = None
