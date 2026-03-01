from __future__ import annotations

from datetime import date
import csv
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db  # se o seu get_db tiver outro nome, me fala e eu ajusto
from app.schemas.finance import (
    FinanceSummaryOut,
    FinanceTransactionCreate,
    FinanceTransactionOut,
    FinanceTransactionUpdate,
    FinanceCategoryOut,
    FinancePaymentMethodOut,
)
from app.api.services.finance_service import FinanceService

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/summary", response_model=FinanceSummaryOut)
def finance_summary(
    tenant_id: int = Query(...),
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    db: Session = Depends(get_db),
):
    try:
        data = FinanceService.get_summary(db, tenant_id=tenant_id, date_from=date_from, date_to=date_to)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions", response_model=dict)
def list_transactions(
    tenant_id: int = Query(...),
    date_from: Optional[date] = Query(None, alias="from"),
    date_to: Optional[date] = Query(None, alias="to"),
    kind: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    payment_method_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = FinanceService.list_transactions(
        db,
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        kind=kind,
        status=status,
        category_id=category_id,
        payment_method_id=payment_method_id,
        page=page,
        limit=limit,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.post("/transactions", response_model=FinanceTransactionOut)
def create_transaction(payload: FinanceTransactionCreate, db: Session = Depends(get_db)):
    try:
        tx = FinanceService.create_transaction(
            db,
            tenant_id=payload.tenant_id,
            user_id=payload.user_id,
            payload=payload.dict(exclude={"tenant_id", "user_id"}),
        )
        return tx
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/transactions/{tx_id}", response_model=FinanceTransactionOut)
def update_transaction(
    tx_id: int,
    tenant_id: int = Query(...),
    payload: FinanceTransactionUpdate = ...,
    db: Session = Depends(get_db),
):
    try:
        tx = FinanceService.update_transaction(
            db,
            tenant_id=tenant_id,
            tx_id=tx_id,
            patch=payload.dict(exclude_unset=True),
        )
        return tx
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/transactions/{tx_id}", response_model=dict)
def delete_transaction(tx_id: int, tenant_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        FinanceService.delete_transaction(db, tenant_id=tenant_id, tx_id=tx_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export")
def export_csv(
    tenant_id: int = Query(...),
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    db: Session = Depends(get_db),
):
    # Exporta as transações do período em CSV (MVP)
    items, _ = FinanceService.list_transactions(
        db,
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        page=1,
        limit=100000,
    )

    def iter_csv():
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id",
            "kind",
            "status",
            "amount_cents",
            "currency",
            "category_id",
            "payment_method_id",
            "patient_name",
            "description",
            "due_date",
            "paid_at",
            "created_at",
        ])
        yield buf.getvalue()
        buf.seek(0); buf.truncate(0)

        for tx in items:
            writer.writerow([
                tx.id,
                tx.kind,
                tx.status,
                tx.amount_cents,
                tx.currency,
                tx.category_id,
                tx.payment_method_id,
                tx.patient_name,
                tx.description,
                tx.due_date.isoformat() if tx.due_date else "",
                tx.paid_at.isoformat() if tx.paid_at else "",
                tx.created_at.isoformat() if tx.created_at else "",
            ])
            yield buf.getvalue()
            buf.seek(0); buf.truncate(0)

    filename = f"finance_{date_from.isoformat()}_{date_to.isoformat()}.csv"
    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/categories", response_model=list[FinanceCategoryOut])
def list_categories(tenant_id: int = Query(...), db: Session = Depends(get_db)):
    return FinanceService.list_categories(db, tenant_id=tenant_id)


@router.get("/payment-methods", response_model=list[FinancePaymentMethodOut])
def list_payment_methods(tenant_id: int = Query(...), db: Session = Depends(get_db)):
    return FinanceService.list_payment_methods(db, tenant_id=tenant_id)