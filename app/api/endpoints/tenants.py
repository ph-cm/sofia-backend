from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.models.user import User
from app.schemas.tenant import TenantProfileOut
from app.api.models.tenant import Tenant
from app.api.models.tenant_integration import TenantIntegration

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get("/tenants/profile/{user_id}")
def get_tenant_profile(user_id: int, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    integration = db.query(TenantIntegration)\
        .filter(TenantIntegration.user_id == user_id)\
        .first()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    return {
        # ===== USERS (DADOS REAIS DO MÉDICO) =====
        "id": user.id,
        "nome": user.nome,
        "timezone": user.timezone,
        "duracao_consulta": user.duracao_consulta,
        "valor_consulta": user.valor_consulta,
        "calendar_id": user.calendar_id,
        "phone_channel": user.phone_channel,

        # ===== TENANT_INTEGRATIONS (BINDING TÉCNICO) =====
        "evolution_instance_name": integration.evolution_instance_id,
        "chatwoot_account_id": integration.chatwoot_account_id,
        "chatwoot_inbox_id": integration.chatwoot_inbox_id,
        "chatwoot_api_token": integration.chatwoot_api_token
    }




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
