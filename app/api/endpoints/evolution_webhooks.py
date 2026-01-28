# app/api/routes/evolution_webhooks.py
from fastapi import APIRouter, Request
from typing import Any, Dict

router = APIRouter(prefix="/webhooks/evolution", tags=["Evolution Webhooks"])

@router.post("/{event}")
async def evolution_webhook(event: str, request: Request):
    payload: Dict[str, Any] = await request.json()

    # log simples pra provar que chegou
    print("EVOLUTION_WEBHOOK:", event)
    # opcional: print(payload)

    # aqui depois você roteia pra Chatwoot / n8n etc
    return {"ok": True, "event": event}
