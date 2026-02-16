from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.models.user import User
from app.schemas.tenant import TenantProfileOut
from app.api.models.tenant import Tenant

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get("/profile/{user_id}", response_model=TenantProfileOut)
def get_tenant_profile(user_id: int, db: Session = Depends(get_db)):

    tenant = db.query(Tenant).filter(Tenant.user_id == user_id).first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return tenant


    # Ajuste nomes conforme seu model User
    # return TenantProfileOut(
    #     user_id=user.id,
    #     nome=user.nome,
    #     inbox_id=getattr(user, "inbox_id", None),
    #     phone_channel=getattr(user, "phone_channel", None),
    #     calendar_id=getattr(user, "calendar_id", "primary") or "primary",
    #     duracao_consulta=getattr(user, "duracao_consulta", 60) or 60,
    #     valor_consulta=getattr(user, "valor_consulta", None),
    #     timezone=getattr(user, "timezone", "America/Sao_Paulo") or "America/Sao_Paulo",
    #     regras={
    #         # começa simples e evolui depois
    #         "oferecer_opcoes": 3,
    #         "antecedencia_min_horas": 2,
    #     },
    # )
