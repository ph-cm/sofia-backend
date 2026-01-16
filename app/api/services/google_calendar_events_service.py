import requests
from dateutil import parser as dateparser
from fastapi import HTTPException

class GoogleCalendarEventsService:
    GOOGLE_CAL_BASE = "https://www.googleapis.com/calendar/v3"

    @staticmethod
    def create_event(
        access_token: str,
        calendar_id: str,
        start_datetime: str,
        end_datetime: str,
        summary: str,
        description: str = "",
        timezone: str = "America/Sao_Paulo",
    ) -> dict:

        # valida ISO e ordem
        try:
            start_dt = dateparser.isoparse(start_datetime)
            end_dt = dateparser.isoparse(end_datetime)
        except Exception:
            raise HTTPException(
                status_code=422,
                detail="start_datetime/end_datetime inválidos (use ISO 8601 com timezone)",
            )

        if end_dt <= start_dt:
            raise HTTPException(status_code=422, detail="end_datetime deve ser maior que start_datetime")

        url = f"{GoogleCalendarEventsService.GOOGLE_CAL_BASE}/calendars/{calendar_id}/events"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        body = {
            "summary": summary,
            "description": description or "",
            "start": {"dateTime": start_datetime, "timeZone": timezone},
            "end": {"dateTime": end_datetime, "timeZone": timezone},
        }

        resp = requests.post(url, headers=headers, json=body, timeout=30)

        if resp.status_code not in (200, 201):
            # token inválido / perms / calendar inválido etc
            raise HTTPException(
                status_code=502,
                detail={
                    "msg": "Falha ao criar evento no Google Calendar",
                    "google_status": resp.status_code,
                    "google_body": resp.text,
                },
            )

        return resp.json()
