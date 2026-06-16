from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ProfileUpdate(BaseModel):
    role_id: Optional[UUID] = None
    active: Optional[bool] = None
