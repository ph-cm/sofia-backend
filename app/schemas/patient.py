from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import date, datetime


class PatientCreateIn(BaseModel):
    tenant_id: int = Field(..., ge=1)
    user_id: int = Field(..., ge=1)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    birth_date: Optional[date] = None
    notes: Optional[str] = None


class PatientUpdateIn(BaseModel):
    tenant_id: int = Field(..., ge=1)
    user_id: int = Field(..., ge=1)
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    birth_date: Optional[date] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class PatientOut(BaseModel):
    id: int
    tenant_id: int
    created_by_user_id: Optional[int] = None
    full_name: str
    phone: str
    email: Optional[str] = None
    birth_date: Optional[date] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatientListOut(BaseModel):
    total: int
    items: List[PatientOut]