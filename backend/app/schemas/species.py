from typing import Optional

from pydantic import BaseModel


class SpeciesCreate(BaseModel):
    code: str
    name: str


class SpeciesUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    active: Optional[bool] = None
