from datetime import date, datetime
from typing import Optional, List, Literal, Dict
from pydantic import BaseModel, Field


Kind = Literal["income", "expense"]
Status = Literal["pending", "paid", "cancelled"]


class FinanceCategoryOut(BaseModel):
    id: int
    # 🔥 tenant_id removido!
    name: str
    is_active: bool

    class Config:
        from_attributes = True # 🔥 Atualizado para Pydantic V2 (tira o Warning do terminal)


class FinancePaymentMethodOut(BaseModel):
    id: int
    # 🔥 tenant_id removido!
    name: str
    is_active: bool

    class Config:
        from_attributes = True # 🔥 Atualizado para Pydantic V2


class FinanceTransactionCreate(BaseModel):
    tenant_id: int
    user_id: int = Field(..., description="created_by_user_id")

    kind: Kind
    status: Status = "pending"
    amount_cents: int = Field(..., ge=0)
    currency: str = "BRL"

    category_id: Optional[int] = None
    payment_method_id: Optional[int] = None

    patient_name: Optional[str] = None
    description: Optional[str] = None

    due_date: Optional[date] = None
    paid_at: Optional[datetime] = None

    appointment_id: Optional[int] = None


class FinanceTransactionUpdate(BaseModel):
    kind: Optional[Kind] = None
    status: Optional[Status] = None
    amount_cents: Optional[int] = Field(None, ge=0)
    currency: Optional[str] = None

    category_id: Optional[int] = None
    payment_method_id: Optional[int] = None

    patient_name: Optional[str] = None
    description: Optional[str] = None

    due_date: Optional[date] = None
    paid_at: Optional[datetime] = None

    appointment_id: Optional[int] = None


class FinanceTransactionOut(BaseModel):
    id: int
    tenant_id: int
    created_by_user_id: int

    kind: str
    status: str
    amount_cents: int
    currency: str

    category_id: Optional[int]
    payment_method_id: Optional[int]

    patient_name: Optional[str]
    description: Optional[str]

    due_date: Optional[date]
    paid_at: Optional[datetime]

    appointment_id: Optional[int]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # 🔥 TROQUE ORM_MODE POR ISSO AQUI


class FinanceSummaryTotals(BaseModel):
    income_cents: int
    expenses_cents: int
    net_cents: int
    receivable_cents: int  # pendente a receber (income pending)


class FinanceBreakdownItem(BaseModel):
    id: Optional[int] = None
    name: str
    amount_cents: int


class FinanceSummaryOut(BaseModel):
    tenant_id: int
    date_from: date
    date_to: date

    totals: FinanceSummaryTotals
    by_category: List[FinanceBreakdownItem]
    by_payment_method: List[FinanceBreakdownItem]
    by_status: Dict[str, int]  # status -> amount_cents