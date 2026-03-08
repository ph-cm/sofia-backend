from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PatientDocumentCreateIn(BaseModel):
    tenant_id: int = Field(..., ge=1)
    user_id: int = Field(..., ge=1)
    title: str = Field(..., min_length=2, max_length=255)
    document_type: str = Field(..., min_length=2, max_length=50)
    file_name: str = Field(..., min_length=2, max_length=255)
    file_url: Optional[str] = None
    mime_type: Optional[str] = None


class PatientDocumentOut(BaseModel):
    id: int
    tenant_id: int
    patient_id: int
    created_by_user_id: Optional[int] = None
    title: str
    document_type: str
    file_name: str
    file_url: Optional[str] = None
    mime_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PatientDocumentListOut(BaseModel):
    total: int
    items: List[PatientDocumentOut]