from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import requests

from sqlalchemy.orm import Session

# ✅ ajuste esses imports para os seus paths reais
from app.api.models.user import User  # <- ajuste se o model tiver outro nome/local
from app.api.services.google_oauth import get_valid_access_token  # <- se já existir, use
# Se não existir, a função fallback está abaixo.

GOOGLE_CAL_BASE = "https://www.googleapis.com/calendar/v3"

def _iso(dt: datetime) -> str:
    # garante timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def _normalize_google_event(item: Dict[str, Any]) -> Dict[str, Any]:
    # Google: all-day => start.date / end.date (end é exclusivo)
    start_obj = item.get("start", {}) or {}
    end_obj = item.get("end", {}) or {}

    all_day = "date" in start_obj

    if all_day:
        # padroniza para ISO (00:00) mas mantém "allDay"
        start = start_obj.get("date")
        end = end_obj.get("date")
        # se vier só YYYY-MM-DD, o front ainda consegue tratar.
        start_out = f"{start}T00:00:00"
        end_out = f"{end}T00:00:00"
    else:
        start_out = start_obj.get("dateTime")
        end_out = end_obj.get("dateTime")

    return {
        "id": item.get("id", ""),
        "title": item.get("summary") or "(Sem título)",
        "start": start_out,
        "end": end_out,
        "allDay": bool(all_day),
        "location": item.get("location"),
        "description": item.get("description"),
    }

def list_events_range(
    db: Session,
    user_id: int,
    calendar_id: str = "primary",
    time_min: Optional[datetime] = None,
    time_max: Optional[datetime] = None,
    telefone: Optional[str] = None,
    max_results: int = 250,
) -> List[Dict[str, Any]]:
    # 1) pega access_token válido
    token = _get_access_token_fallback(db, user_id)

    # 2) monta query
    params: Dict[str, Any] = {
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": max_results,
    }
    if time_min:
        params["timeMin"] = _iso(time_min)
    if time_max:
        params["timeMax"] = _iso(time_max)

    # filtro livre do Google (q) — funciona bem para telefone em summary/description
    # (se o seu uso for forte, vale manter como filtro opcional do backend)
    if telefone:
        params["q"] = telefone

    url = f"{GOOGLE_CAL_BASE}/calendars/{calendar_id}/events"
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(url, headers=headers, params=params, timeout=30)
    if res.status_code >= 400:
        # retorna erro “explicável”
        try:
            payload = res.json()
        except Exception:
            payload = {"raw": res.text}
        raise RuntimeError(f"Google API error {res.status_code}: {payload}")

    data = res.json()
    items = data.get("items") or []

    return [_normalize_google_event(it) for it in items]

# -------------------------------------------------------
# Fallback: se você NÃO tiver get_valid_access_token pronto
# -------------------------------------------------------
def _get_access_token_fallback(db: Session, user_id: int) -> str:
    """
    ✅ Sem alterar nada existente: tenta só ler token já salvo.
    Se você já tem refresh automático em outro lugar, substitua por ele.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise RuntimeError("user_id não encontrado")

    # ajuste os nomes conforme seu model real
    token = getattr(user, "google_access_token", None)
    if not token:
        raise RuntimeError("Google não conectado (sem google_access_token)")

    return token
