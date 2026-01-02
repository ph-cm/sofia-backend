import requests
from app.core.config import settings

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

def refresh_google_access_token(refresh_token: str):
    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(GOOGLE_TOKEN_URL, data=data, headers=headers)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()
