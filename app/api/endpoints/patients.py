from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.api.services.patient_service import PatientService
from app.schemas.patient import (
    PatientCreateIn,
    PatientUpdateIn,
    PatientOut,
    PatientListOut,
)
from app.schemas.patient_document import (
    PatientDocumentCreateIn,
    PatientDocumentOut,
    PatientDocumentListOut,
)

router = APIRouter(prefix="/patients", tags=["Patients"])


def _ensure_same_user(payload_user_id: int, current_user: dict):
    if current_user["id"] != payload_user_id:
        raise HTTPException(status_code=403, detail="Usuário sem permissão")


@router.post("", response_model=PatientOut)
def create_patient(
    payload: PatientCreateIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_same_user(payload.user_id, current_user)
    return PatientService.create_patient(db, payload)


@router.get("", response_model=PatientListOut)
def list_patients(
    tenant_id: int = Query(..., ge=1),
    search: str | None = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    items = PatientService.list_patients(
        db=db,
        tenant_id=tenant_id,
        search=search,
        active_only=active_only,
    )
    return {"total": len(items), "items": items}


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: int,
    tenant_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    return PatientService.get_patient(db, tenant_id, patient_id)


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: int,
    payload: PatientUpdateIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_same_user(payload.user_id, current_user)
    return PatientService.update_patient(db, patient_id, payload)


@router.delete("/{patient_id}")
def delete_patient(
    patient_id: int,
    tenant_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    return PatientService.delete_patient(db, tenant_id, patient_id)


@router.post("/{patient_id}/documents", response_model=PatientDocumentOut)
def create_patient_document(
    patient_id: int,
    payload: PatientDocumentCreateIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_same_user(payload.user_id, current_user)
    return PatientService.create_document(
        db=db,
        tenant_id=payload.tenant_id,
        patient_id=patient_id,
        payload=payload,
    )


@router.get("/{patient_id}/documents", response_model=PatientDocumentListOut)
def list_patient_documents(
    patient_id: int,
    tenant_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    items = PatientService.list_documents(db, tenant_id, patient_id)
    return {"total": len(items), "items": items}


@router.delete("/{patient_id}/documents/{document_id}")
def delete_patient_document(
    patient_id: int,
    document_id: int,
    tenant_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    return PatientService.delete_document(db, tenant_id, patient_id, document_id)