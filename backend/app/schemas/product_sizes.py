from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ProductSizeCreate(BaseModel):
    species_id: UUID
    size_code: str
    description: Optional[str] = None


class ProductSizeUpdate(BaseModel):
    species_id: Optional[UUID] = None
    size_code: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
