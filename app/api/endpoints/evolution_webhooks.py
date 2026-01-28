# app/api/routes/evolution_webhooks.py
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from collections import deque

from app.core.security import verify_n8n_api_key  # só se você quiser proteger o inspector
from app.core.config import settings

router = APIRouter(prefix="/webhooks/evolution", tags=["Evolution Webhooks"])

# guarda os últimos 200 eventos em memória
_EVENTS = deque(maxlen=200)

def _now():
    return datetime.now(timezone.utc)

@router.post("")
async def evolution_webhook_receiver(request: Request):
    """
    Receiver real do Evolution.
    Valida um token simples na querystring pra evitar qualquer um spammar.
    Ex: WEBHOOK_GLOBAL_URL=https://api.../webhooks/evolution?token=XYZ
    """
    token = request.query_params.get("token")
    if getattr(settings, "EVOLUTION_WEBHOOK_SECRET", None):
        if token != settings.EVOLUTION_WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="Invalid webhook token")

    try:
        body = await request.json()
    except Exception:
        body = {"_raw": (await request.body()).decode("utf-8", errors="ignore")}

    item = {
        "received_at": _now().isoformat(),
        "headers": {
            # pega alguns headers úteis
            "user-agent": request.headers.get("user-agent"),
            "content-type": request.headers.get("content-type"),
            "x-forwarded-for": request.headers.get("x-forwarded-for"),
        },
        "payload": body,
    }
    _EVENTS.appendleft(item)

    return {"ok": True}

@router.get("/last", dependencies=[Depends(verify_n8n_api_key)])
def evolution_webhook_last(limit: int = Query(10, ge=1, le=200)):
    return {"ok": True, "count": min(limit, len(_EVENTS)), "events": list(_EVENTS)[:limit]}

@router.get("/health", dependencies=[Depends(verify_n8n_api_key)])
def evolution_webhook_health(within_seconds: int = Query(60, ge=5, le=3600)):
    if not _EVENTS:
        return {"ok": True, "received_recently": False, "last_received_at": None}

    last = _EVENTS[0]
    last_dt = datetime.fromisoformat(last["received_at"])
    recent = (_now() - last_dt) <= timedelta(seconds=within_seconds)

    return {
        "ok": True,
        "received_recently": recent,
        "last_received_at": last["received_at"],
        "within_seconds": within_seconds,
    }
