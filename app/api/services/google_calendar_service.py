import requests
from datetime import datetime

GOOGLE_FREEBUSY_URL = "https://www.googleapis.com/calendar/v3/freeBusy"


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
