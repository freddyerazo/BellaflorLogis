from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class VarietyCreate(BaseModel):
    species_id: UUID
    code: Optional[str] = None
    name: str


class VarietyUpdate(BaseModel):
    species_id: Optional[UUID] = None
    code: Optional[str] = None
    name: Optional[str] = None
    active: Optional[bool] = None
