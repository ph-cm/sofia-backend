import requests
from sqlalchemy.orm import Session
from app.api.services.google_token_service import GoogleTokenService

GOOGLE_CALENDAR_LIST_URL = "https://www.googleapis.com/calendar/v3/users/me/calendarList"


def list_calendars(db: Session, token):
    headers = {
        "Authorization": f"Bearer {token.google_access_token}"
    }

    response = requests.get(GOOGLE_CALENDAR_LIST_URL, headers=headers)

    # 🔁 TOKEN EXPIRADO → REFRESH
    if response.status_code == 401:
        token = GoogleTokenService.refresh_access_token(db, token)

        headers["Authorization"] = f"Bearer {token.google_access_token}"
        response = requests.get(GOOGLE_CALENDAR_LIST_URL, headers=headers)

    # ❌ qualquer erro que não seja sucesso
    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()
