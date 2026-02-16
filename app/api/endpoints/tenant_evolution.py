from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from requests import Session
from app.db.session import SessionLocal
from app.api.models.tenant import Tenant
from app.api.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["Tenants"])


class BindInstanceIn(BaseModel):
    instance_name: str


class ChatwootConfigIn(BaseModel):
    chatwoot_account_id: int
    chatwoot_inbox_id: int
    chatwoot_api_token: str

class TenantCreateIn(BaseModel):
    name: str
    user_id: int
    
@router.post("")
def create_tenant(body: TenantCreateIn):
    db: Session = SessionLocal()
    try:
        t = Tenant(name=body.name, user_id=body.user_id)
        db.add(t)
        db.commit()
        db.refresh(t)
        return {"ok": True, "tenant": {"id": t.id, "name": t.name, "user_id": t.user_id}}
    finally:
        db.close()

@router.post("/{tenant_id}/evolution/bind")
def bind_evolution_instance(tenant_id: int, body: BindInstanceIn):
    try:
        out = TenantService.bind_evolution_instance(tenant_id=tenant_id, instance_name=body.instance_name)
        return {"ok": True, "tenant": out}
    except ValueError as e:
        if str(e) == "tenant_not_found":
            raise HTTPException(status_code=404, detail="Tenant not found")
        raise


@router.post("/{tenant_id}/chatwoot/config")
def set_chatwoot_config(tenant_id: int, body: ChatwootConfigIn):
    try:
        out = TenantService.set_chatwoot_config(
            tenant_id=tenant_id,
            account_id=body.chatwoot_account_id,
            inbox_id=body.chatwoot_inbox_id,
            api_token=body.chatwoot_api_token,
        )
        return {"ok": True, "tenant": out}
    except ValueError as e:
        if str(e) == "tenant_not_found":
            raise HTTPException(status_code=404, detail="Tenant not found")
        raise
