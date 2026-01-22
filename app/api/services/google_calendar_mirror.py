from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import requests

from sqlalchemy.orm import Session

from app.api.services.google_token_service import GoogleTokenService  # ✅ usa o seu service existente

GOOGLE_CAL_BASE = "https://www.googleapis.com/calendar/v3"


def _iso(dt: datetime) -> str:
    # garante timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _normalize_google_event(item: Dict[str, Any]) -> Dict[str, Any]:
    start_obj = item.get("start", {}) or {}
    end_obj = item.get("end", {}) or {}

    all_day = "date" in start_obj

    if all_day:
        start = start_obj.get("date")  # YYYY-MM-DD
        end = end_obj.get("date")      # YYYY-MM-DD (exclusive)
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
    # ✅ aqui é o ponto principal: usa o token service que já funciona
    token = GoogleTokenService.get_valid_access_token(db=db, user_id=user_id)

    params: Dict[str, Any] = {
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": max_results,
    }
    if time_min:
        params["timeMin"] = _iso(time_min)
    if time_max:
        params["timeMax"] = _iso(time_max)

    # filtro de texto do Google Calendar (summary/description etc)
    if telefone:
        params["q"] = telefone

    url = f"{GOOGLE_CAL_BASE}/calendars/{calendar_id}/events"
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(url, headers=headers, params=params, timeout=30)

    # ✅ erro amigável
    if res.status_code >= 400:
        try:
            payload = res.json()
        except Exception:
            payload = {"raw": res.text}
        raise RuntimeError(f"Google API error {res.status_code}: {payload}")

    data = res.json()
    items = data.get("items") or []
    return [_normalize_google_event(it) for it in items]
