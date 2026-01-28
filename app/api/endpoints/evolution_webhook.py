from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
import json

router = APIRouter(prefix="/webhooks", tags=["Evolution Webhook"])


@router.post("/evolution")
async def evolution_webhook(request: Request):
    """
    Webhook GLOBAL do Evolution API.
    Recebe eventos de TODAS as instâncias (multi-tenant).
    """
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # LOG BRUTO (importante nessa fase)
    print("🔥 EVOLUTION WEBHOOK RECEBIDO")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    # Campos importantes (variam por evento)
    instance_name = (
        payload.get("instance")
        or payload.get("instanceName")
        or (payload.get("data") or {}).get("instance")
    )

    event = payload.get("event") or payload.get("type")

    if not instance_name:
        print("⚠️ Webhook sem instanceName")
        return {"ok": True}

    print(f"➡️ Tenant: {instance_name}")
    print(f"➡️ Evento: {event}")

    # A partir daqui você pode:
    # - salvar no banco
    # - chamar um service
    # - disparar n8n
    # - integrar Chatwoot

    return {"ok": True}
