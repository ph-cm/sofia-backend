import requests
from datetime import datetime
from app.api.services.google_token_service import GoogleTokenService

GOOGLE_FREEBUSY_URL = "https://www.googleapis.com/calendar/v3/freeBusy"
GOOGLE_DELETE_EVENT_URL = "https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events/{eventId}"

class GoogleCalendarService:

    def get_availability(self, token, start_date, end_date, timezone):
        headers = {
            "Authorization": f"Bearer {token.google_access_token}",
            "Content-Type": "application/json"
        }

        body = {
            "timeMin": start_date,
            "timeMax": end_date,
            "timeZone": timezone,
            "items": [{"id": "primary"}]
        }

        response = requests.post(GOOGLE_FREEBUSY_URL, json=body, headers=headers)

        # token expirado → tenta refresh
        if response.status_code == 401:
            from app.api.services.google_token_service import GoogleTokenService
            token = GoogleTokenService.refresh_access_token(token.db, token)
            headers["Authorization"] = f"Bearer {token.google_access_token}"
            response = requests.post(GOOGLE_FREEBUSY_URL, json=body, headers=headers)

        if response.status_code != 200:
            raise Exception(response.text)

        data = response.json()
        busy = data["calendars"]["primary"]["busy"]

        return self._busy_to_free(start_date, end_date, busy)

    def _busy_to_free(self, start_date, end_date, busy_intervals):
        free = []
        cursor = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        for interval in busy_intervals:
            busy_start = datetime.fromisoformat(interval["start"])
            busy_end = datetime.fromisoformat(interval["end"])

            if cursor < busy_start:
                free.append({
                    "inicio": cursor.isoformat(),
                    "fim": busy_start.isoformat()
                })

            cursor = max(cursor, busy_end)

        if cursor < end_dt:
            free.append({
                "inicio": cursor.isoformat(),
                "fim": end_dt.isoformat()
            })

        return free
    
    def update_event(
    self,
    token,
    calendar_id: str,
    event_id: str,
    title: str,
    description: str,
    start: str,
    end: str,
    timezone: str
    ):
        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}"

        headers = {
            "Authorization": f"Bearer {token.google_access_token}",
            "Content-Type": "application/json"
        }

        body = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start,
                "timeZone": timezone
            },
            "end": {
                "dateTime": end,
                "timeZone": timezone
            }
        }

        response = requests.patch(url, json=body, headers=headers)

        # 🔥 TOKEN EXPIRADO → REFRESH AUTOMÁTICO
        if response.status_code == 401:
            token = GoogleTokenService.refresh_access_token(token.db, token)
            headers["Authorization"] = f"Bearer {token.google_access_token}"
            response = requests.patch(url, json=body, headers=headers)

        if response.status_code not in (200, 201):
            raise Exception(f"Erro ao atualizar evento: {response.text}")

        return response.json()

    
    def list_events(self, token, calendar_id: str):

        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"

        headers = {
            "Authorization": f"Bearer {token.google_access_token}",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Erro ao listar eventos: {response.text}")

        data = response.json()
        return data.get("items", [])





    def delete_event(self, db, token, calendar_id: str, event_id: str):
        url = GOOGLE_DELETE_EVENT_URL.format(calendarId=calendar_id, eventId=event_id)

        headers = {"Authorization": f"Bearer {token.google_access_token}"}
        response = requests.delete(url, headers=headers)

        if response.status_code == 401:
            token = GoogleTokenService.refresh_access_token(db, token)
            headers["Authorization"] = f"Bearer {token.google_access_token}"
            response = requests.delete(url, headers=headers)

        if response.status_code not in (200, 204):
            raise Exception(f"Erro ao deletar evento: {response.text}")

        return True


google_calendar_service = GoogleCalendarService()
