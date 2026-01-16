import requests

class GoogleCalendarEventsService:
    GOOGLE_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"

    @staticmethod
    def create_event(
        access_token: str,
        calendar_id: str,
        start_datetime: str,
        end_datetime: str,
        summary: str,
        description: str,
        timezone: str,
    ):
        url = GoogleCalendarEventsService.GOOGLE_EVENTS_URL.format(calendar_id=calendar_id)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_datetime, "timeZone": timezone},
            "end": {"dateTime": end_datetime, "timeZone": timezone},
        }

        r = requests.post(url, json=body, headers=headers)
        if r.status_code not in (200, 201):
            raise Exception(f"Erro ao criar evento: {r.text}")

        return r.json()
