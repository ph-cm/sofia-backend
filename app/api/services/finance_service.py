from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_

from app.api.models.finance_transaction import FinanceTransaction
from app.api.models.finance_category import FinanceCategory
from app.api.models.finance_paymente_method import FinancePaymentMethod


class FinanceService:
    # ------------------------
    # Transactions CRUD
    # ------------------------
    @staticmethod
    def create_transaction(db: Session, *, tenant_id: int, user_id: int, payload: Dict[str, Any]) -> FinanceTransaction:
        tx = FinanceTransaction(
            tenant_id=tenant_id,
            created_by_user_id=user_id,
            kind=payload["kind"],
            status=payload.get("status", "pending"),
            amount_cents=payload["amount_cents"],
            currency=payload.get("currency", "BRL"),
            category_id=payload.get("category_id"),
            payment_method_id=payload.get("payment_method_id"),
            patient_name=payload.get("patient_name"),
            description=payload.get("description"),
            due_date=payload.get("due_date"),
            paid_at=payload.get("paid_at"),
            appointment_id=payload.get("appointment_id"),
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    @staticmethod
    def get_transaction(db: Session, *, tenant_id: int, tx_id: int) -> Optional[FinanceTransaction]:
        return (
            db.query(FinanceTransaction)
            .filter(FinanceTransaction.tenant_id == tenant_id, FinanceTransaction.id == tx_id)
            .first()
        )

    @staticmethod
    def update_transaction(db: Session, *, tenant_id: int, tx_id: int, patch: Dict[str, Any]) -> FinanceTransaction:
        tx = FinanceService.get_transaction(db, tenant_id=tenant_id, tx_id=tx_id)
        if not tx:
            raise ValueError("Transaction not found")

        for k, v in patch.items():
            if v is not None:
                setattr(tx, k, v)

        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    @staticmethod
    def delete_transaction(db: Session, *, tenant_id: int, tx_id: int) -> None:
        tx = FinanceService.get_transaction(db, tenant_id=tenant_id, tx_id=tx_id)
        if not tx:
            raise ValueError("Transaction not found")
        db.delete(tx)
        db.commit()

    @staticmethod
    def list_transactions(
        db: Session,
        *,
        tenant_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        kind: Optional[str] = None,
        status: Optional[str] = None,
        category_id: Optional[int] = None,
        payment_method_id: Optional[int] = None,
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[FinanceTransaction], int]:
        q = db.query(FinanceTransaction).filter(FinanceTransaction.tenant_id == tenant_id)

        # filtro de período: usa created_at (MVP)
        if date_from:
            q = q.filter(func.date(FinanceTransaction.created_at) >= date_from)
        if date_to:
            q = q.filter(func.date(FinanceTransaction.created_at) <= date_to)

        if kind:
            q = q.filter(FinanceTransaction.kind == kind)
        if status:
            q = q.filter(FinanceTransaction.status == status)
        if category_id:
            q = q.filter(FinanceTransaction.category_id == category_id)
        if payment_method_id:
            q = q.filter(FinanceTransaction.payment_method_id == payment_method_id)

        total = q.count()

        items = (
            q.order_by(FinanceTransaction.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        return items, total

    # ------------------------
    # Summary / KPIs
    # ------------------------
    @staticmethod
    def get_summary(db: Session, *, tenant_id: int, date_from: date, date_to: date) -> Dict[str, Any]:
        base = db.query(FinanceTransaction).filter(
            FinanceTransaction.tenant_id == tenant_id,
            func.date(FinanceTransaction.created_at) >= date_from,
            func.date(FinanceTransaction.created_at) <= date_to,
        )

        income_sum = db.query(func.coalesce(func.sum(FinanceTransaction.amount_cents), 0)).filter(
            FinanceTransaction.tenant_id == tenant_id,
            func.date(FinanceTransaction.created_at) >= date_from,
            func.date(FinanceTransaction.created_at) <= date_to,
            FinanceTransaction.kind == "income",
            FinanceTransaction.status != "cancelled",
        ).scalar() or 0

        expenses_sum = db.query(func.coalesce(func.sum(FinanceTransaction.amount_cents), 0)).filter(
            FinanceTransaction.tenant_id == tenant_id,
            func.date(FinanceTransaction.created_at) >= date_from,
            func.date(FinanceTransaction.created_at) <= date_to,
            FinanceTransaction.kind == "expense",
            FinanceTransaction.status != "cancelled",
        ).scalar() or 0

        receivable_sum = db.query(func.coalesce(func.sum(FinanceTransaction.amount_cents), 0)).filter(
            FinanceTransaction.tenant_id == tenant_id,
            func.date(FinanceTransaction.created_at) >= date_from,
            func.date(FinanceTransaction.created_at) <= date_to,
            FinanceTransaction.kind == "income",
            FinanceTransaction.status == "pending",
        ).scalar() or 0

        net_sum = int(income_sum) - int(expenses_sum)

        # by_category (somando só income não cancelado por padrão)
        # by_category
        by_category_rows = (
            db.query(
                FinanceCategory.id,
                FinanceCategory.name,
                func.coalesce(func.sum(FinanceTransaction.amount_cents), 0).label("amount_cents"),
            )
            .join(FinanceTransaction, FinanceTransaction.category_id == FinanceCategory.id)
            .filter(
                FinanceTransaction.tenant_id == tenant_id, # Transação filtra por tenant!
                func.date(FinanceTransaction.created_at) >= date_from,
                func.date(FinanceTransaction.created_at) <= date_to,
                FinanceTransaction.kind == "income",
                FinanceTransaction.status != "cancelled",
            )
            .group_by(FinanceCategory.id, FinanceCategory.name)
            .order_by(func.sum(FinanceTransaction.amount_cents).desc())
            .all()
        )

        # by_payment_method
        by_payment_rows = (
            db.query(
                FinancePaymentMethod.id,
                FinancePaymentMethod.name,
                func.coalesce(func.sum(FinanceTransaction.amount_cents), 0).label("amount_cents"),
            )
            .join(FinanceTransaction, FinanceTransaction.payment_method_id == FinancePaymentMethod.id)
            .filter(
                FinanceTransaction.tenant_id == tenant_id, # Transação filtra por tenant!
                func.date(FinanceTransaction.created_at) >= date_from,
                func.date(FinanceTransaction.created_at) <= date_to,
                FinanceTransaction.kind == "income",
                FinanceTransaction.status != "cancelled",
            )
            .group_by(FinancePaymentMethod.id, FinancePaymentMethod.name)
            .order_by(func.sum(FinanceTransaction.amount_cents).desc())
            .all()
        )

        # by_status (soma amount por status, inclui income e expense, exceto cancelado? — deixei incluir cancelado também pra painel)
        by_status_rows = (
            db.query(
                FinanceTransaction.status,
                func.coalesce(func.sum(FinanceTransaction.amount_cents), 0).label("amount_cents"),
            )
            .filter(
                FinanceTransaction.tenant_id == tenant_id,
                func.date(FinanceTransaction.created_at) >= date_from,
                func.date(FinanceTransaction.created_at) <= date_to,
            )
            .group_by(FinanceTransaction.status)
            .all()
        )

        by_status = {r.status: int(r.amount_cents) for r in by_status_rows}

        return {
            "tenant_id": tenant_id,
            "date_from": date_from,
            "date_to": date_to,
            "totals": {
                "income_cents": int(income_sum),
                "expenses_cents": int(expenses_sum),
                "net_cents": int(net_sum),
                "receivable_cents": int(receivable_sum),
            },
            "by_category": [
                {"id": int(r.id), "name": r.name, "amount_cents": int(r.amount_cents)} for r in by_category_rows
            ],
            "by_payment_method": [
                {"id": int(r.id), "name": r.name, "amount_cents": int(r.amount_cents)} for r in by_payment_rows
            ],
            "by_status": by_status,
        }

    # ------------------------
    # Categories & Payment methods (MVP helpers)
    # ------------------------
    @staticmethod
    def list_categories(db: Session, *, tenant_id: int) -> List[FinanceCategory]:
        # Busca todas as categorias globais, ignora o tenant_id
        return db.query(FinanceCategory).order_by(FinanceCategory.name.asc()).all()

    @staticmethod
    def list_payment_methods(db: Session, *, tenant_id: int) -> List[FinancePaymentMethod]:
        # Busca todos os métodos globais, ignora o tenant_id
        return db.query(FinancePaymentMethod).order_by(FinancePaymentMethod.name.asc()).all()