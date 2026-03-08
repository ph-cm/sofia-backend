from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException
from typing import Optional

from app.api.models.patient import Patient
from app.api.models.patient_document import PatientDocument
from app.schemas.patient import PatientCreateIn, PatientUpdateIn
from app.schemas.patient_document import PatientDocumentCreateIn


class PatientService:

    @staticmethod
    def create_patient(db: Session, payload: PatientCreateIn) -> Patient:
        patient = Patient(
            tenant_id=payload.tenant_id,
            created_by_user_id=payload.user_id,
            full_name=payload.full_name.strip(),
            phone=payload.phone.strip(),
            email=payload.email.strip() if payload.email else None,
            birth_date=payload.birth_date,
            notes=payload.notes.strip() if payload.notes else None,
            is_active=True,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient

    @staticmethod
    def list_patients(
        db: Session,
        tenant_id: int,
        search: Optional[str] = None,
        active_only: bool = True,
    ) -> list[Patient]:
        query = db.query(Patient).filter(Patient.tenant_id == tenant_id)

        if active_only:
            query = query.filter(Patient.is_active == True)

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Patient.full_name.ilike(term),
                    Patient.phone.ilike(term),
                    Patient.email.ilike(term),
                )
            )

        return query.order_by(Patient.full_name.asc()).all()

    @staticmethod
    def get_patient(db: Session, tenant_id: int, patient_id: int) -> Patient:
        patient = (
            db.query(Patient)
            .filter(Patient.id == patient_id, Patient.tenant_id == tenant_id)
            .first()
        )
        if not patient:
            raise HTTPException(status_code=404, detail="Paciente não encontrado")
        return patient

    @staticmethod
    def update_patient(db: Session, patient_id: int, payload: PatientUpdateIn) -> Patient:
        patient = PatientService.get_patient(db, payload.tenant_id, patient_id)

        if payload.full_name is not None:
            patient.full_name = payload.full_name.strip()

        if payload.phone is not None:
            patient.phone = payload.phone.strip()

        if payload.email is not None:
            patient.email = payload.email.strip() if payload.email else None

        if payload.birth_date is not None:
            patient.birth_date = payload.birth_date

        if payload.notes is not None:
            patient.notes = payload.notes.strip() if payload.notes else None

        if payload.is_active is not None:
            patient.is_active = payload.is_active

        db.commit()
        db.refresh(patient)
        return patient

    @staticmethod
    def delete_patient(db: Session, tenant_id: int, patient_id: int) -> dict:
        patient = PatientService.get_patient(db, tenant_id, patient_id)
        patient.is_active = False
        db.commit()
        return {"status": "deleted", "patient_id": patient_id}

    @staticmethod
    def create_document(
        db: Session,
        tenant_id: int,
        patient_id: int,
        payload: PatientDocumentCreateIn,
    ) -> PatientDocument:
        PatientService.get_patient(db, tenant_id, patient_id)

        doc = PatientDocument(
            tenant_id=tenant_id,
            patient_id=patient_id,
            created_by_user_id=payload.user_id,
            title=payload.title.strip(),
            document_type=payload.document_type.strip(),
            file_name=payload.file_name.strip(),
            file_url=payload.file_url.strip() if payload.file_url else None,
            mime_type=payload.mime_type.strip() if payload.mime_type else None,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def list_documents(db: Session, tenant_id: int, patient_id: int) -> list[PatientDocument]:
        PatientService.get_patient(db, tenant_id, patient_id)

        return (
            db.query(PatientDocument)
            .filter(
                PatientDocument.tenant_id == tenant_id,
                PatientDocument.patient_id == patient_id,
            )
            .order_by(PatientDocument.created_at.desc())
            .all()
        )

    @staticmethod
    def delete_document(db: Session, tenant_id: int, patient_id: int, document_id: int) -> dict:
        PatientService.get_patient(db, tenant_id, patient_id)

        doc = (
            db.query(PatientDocument)
            .filter(
                PatientDocument.id == document_id,
                PatientDocument.tenant_id == tenant_id,
                PatientDocument.patient_id == patient_id,
            )
            .first()
        )

        if not doc:
            raise HTTPException(status_code=404, detail="Documento não encontrado")

        db.delete(doc)
        db.commit()
        return {"status": "deleted", "document_id": document_id}