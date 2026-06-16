from typing import Optional

from pydantic import BaseModel


class CustomerCreate(BaseModel):
    customer_code: str
    customer_name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class CustomerUpdate(BaseModel):
    customer_code: Optional[str] = None
    customer_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    active: Optional[bool] = None
