from pydantic import BaseModel
from typing import List, Optional

class AnalyticsKpis(BaseModel):
    totalAppointments: int
    confirmedAppointments: int
    completedAppointments: int
    cancelledAppointments: int
    noShowAppointments: int
    grossRevenue: float
    pendingRevenue: float
    avgTicket: float
    conversionRate: float


class AnalyticsBreakdownItem(BaseModel):
    status: str
    count: int


class AnalyticsRecentItem(BaseModel):
    id: int
    patientName: Optional[str]
    startAt: str
    status: str


class AnalyticsResponse(BaseModel):
    tenant_id: int
    from_: str
    to: str
    kpis: AnalyticsKpis
    breakdown: List[AnalyticsBreakdownItem]
    recent: List[AnalyticsRecentItem]