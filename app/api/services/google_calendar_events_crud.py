# app/api/services/google_calendar_events_crud.py
from __future__ import annotations

from typing import Any, Dict, Optional, List
import requests
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from app.api.services.google_token_service import GoogleTokenService

GOOGLE_CAL_BASE = "https://www.googleapis.com/calendar/v3"


def _iso(dt: datetime) -> str:
    # garante tz
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def normalize_google_event(item: Dict[str, Any]) -> Dict[str, Any]:
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


class GoogleCalendarEventsCRUD:
    """
    CRUD normalizado para a Agenda (fonte da verdade = Google).

    Observação:
    - Não faz refresh manual aqui: assume que get_valid_access_token já entrega token válido.
    - Se você quiser mirror local, chame seu mirror service no router, após cada operação.
    """

    def create(
        self,
        db: Session,
        user_id: int,
        calendar_id: str,
        title: str,
        start: str,  # RFC3339 com offset
        end: str,    # RFC3339 com offset
        timezone_str: str = "America/Sao_Paulo",
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        token = GoogleTokenService.get_valid_access_token_agenda(db=db, user_id=user_id)

        url = f"{GOOGLE_CAL_BASE}/calendars/{calendar_id}/events"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        body: Dict[str, Any] = {
            "summary": title or "(Sem título)",
            "start": {"dateTime": start, "timeZone": timezone_str},
            "end": {"dateTime": end, "timeZone": timezone_str},
        }
        if description is not None:
            body["description"] = description
        if location is not None:
            body["location"] = location

        res = requests.post(url, json=body, headers=headers, timeout=30)
        if res.status_code not in (200, 201):
            try:
                payload = res.json()
            except Exception:
                payload = {"raw": res.text}
            raise RuntimeError(f"Google create error {res.status_code}: {payload}")

        return normalize_google_event(res.json())

    def update(
        self,
        db: Session,
        user_id: int,
        calendar_id: str,
        event_id: str,
        title: str,
        start: str,
        end: str,
        timezone_str: str = "America/Sao_Paulo",
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        token = GoogleTokenService.get_valid_access_token(db=db, user_id=user_id)

        url = f"{GOOGLE_CAL_BASE}/calendars/{calendar_id}/events/{event_id}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Se description/location vierem None, a gente não apaga.
        # Se você quiser permitir "limpar", mande "" do front.
        body: Dict[str, Any] = {
            "summary": title or "(Sem título)",
            "start": {"dateTime": start, "timeZone": timezone_str},
            "end": {"dateTime": end, "timeZone": timezone_str},
        }
        if description is not None:
            body["description"] = description
        if location is not None:
            body["location"] = location

        res = requests.patch(url, json=body, headers=headers, timeout=30)
        if res.status_code not in (200, 201):
            try:
                payload = res.json()
            except Exception:
                payload = {"raw": res.text}
            raise RuntimeError(f"Google update error {res.status_code}: {payload}")

        return normalize_google_event(res.json())

    def delete(
        self,
        db: Session,
        user_id: int,
        calendar_id: str,
        event_id: str,
    ) -> bool:
        token = GoogleTokenService.get_valid_access_token_agenda(db=db, user_id=user_id)

        url = f"{GOOGLE_CAL_BASE}/calendars/{calendar_id}/events/{event_id}"
        headers = {"Authorization": f"Bearer {token}"}

        res = requests.delete(url, headers=headers, timeout=30)
        if res.status_code not in (200, 204):
            try:
                payload = res.json()
            except Exception:
                payload = {"raw": res.text}
            raise RuntimeError(f"Google delete error {res.status_code}: {payload}")

        return True

    def list_range(
        self,
        db: Session,
        user_id: int,
        calendar_id: str,
        time_min: Optional[datetime],
        time_max: Optional[datetime],
        telefone: Optional[str] = None,
        max_results: int = 250,
    ) -> List[Dict[str, Any]]:
        token = GoogleTokenService.get_valid_access_token_agenda(db=db, user_id=user_id)

        params: Dict[str, Any] = {
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": max_results,
        }
        if time_min:
            params["timeMin"] = _iso(time_min)
        if time_max:
            params["timeMax"] = _iso(time_max)
        if telefone:
            params["q"] = telefone

        url = f"{GOOGLE_CAL_BASE}/calendars/{calendar_id}/events"
        headers = {"Authorization": f"Bearer {token}"}

        res = requests.get(url, headers=headers, params=params, timeout=30)
        if res.status_code >= 400:
            try:
                payload = res.json()
            except Exception:
                payload = {"raw": res.text}
            raise RuntimeError(f"Google list error {res.status_code}: {payload}")

        data = res.json()
        items = data.get("items") or []
        return [normalize_google_event(it) for it in items]


google_calendar_events_crud = GoogleCalendarEventsCRUD()