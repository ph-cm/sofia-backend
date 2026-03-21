from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from app.core.config import settings

from datetime import datetime, timezone
from urllib.parse import urlencode
import requests


class GoogleAuthService:
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.scopes = settings.GOOGLE_SCOPES.split(",")

    # =========================
    # LEGADO / COMPARTILHADO
    # =========================
    def auth_url(self, user_id: int):
        params = {
            "client_id": self.client_id,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": str(user_id),
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def exchange_code(self, code: str):
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise Exception(f"Falha ao trocar code por token (legado): {response.text}")

        data = response.json()
        expires_in = int(data.get("expires_in", 3600))

        return {
            "access": data["access_token"],
            "refresh": data.get("refresh_token"),
            "expires_in": expires_in,
            "scope": data.get("scope"),
            "token_type": data.get("token_type"),
        }

    def refresh_access_token(self, access_token: str, refresh_token: str):
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
        )

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())

        return {
            "access": creds.token,
            "expiry": creds.expiry,
        }

    # =========================
    # NOVO / ISOLADO PARA AGENDA
    # sem Flow, sem PKCE, troca manual
    # =========================
    def auth_url_agenda(self, user_id: int):
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI_AGENDA,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": str(user_id),
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def exchange_code_agenda(self, code: str):
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI_AGENDA,
                "grant_type": "authorization_code",
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise Exception(f"Falha ao trocar code por token (agenda): {response.text}")

        data = response.json()

        expires_in = int(data.get("expires_in", 3600))

        return {
            "access": data["access_token"],
            "refresh": data.get("refresh_token"),
            "expires_in": expires_in,
            "scope": data.get("scope"),
            "token_type": data.get("token_type"),
        }
class GoogleAuthService:
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.scopes = settings.GOOGLE_SCOPES.split(",")

    def auth_url(self, user_id: int):
        params = {
            "client_id": self.client_id,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": str(user_id),
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def exchange_code(self, code: str):
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise Exception(f"Falha ao trocar code por token (legado): {response.text}")

        data = response.json()
        expires_in = int(data.get("expires_in", 3600))

        return {
            "access": data["access_token"],
            "refresh": data.get("refresh_token"),
            "expires_in": expires_in,
            "scope": data.get("scope"),
            "token_type": data.get("token_type"),
        }

    def refresh_access_token(self, access_token: str, refresh_token: str):
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
        )

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())

        return {
            "access": creds.token,
            "expiry": creds.expiry,
        }

    def auth_url_agenda(self, user_id: int):
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI_AGENDA,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": str(user_id),
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def exchange_code_agenda(self, code: str):
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI_AGENDA,
                "grant_type": "authorization_code",
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise Exception(f"Falha ao trocar code por token (agenda): {response.text}")

        data = response.json()

        expires_in = int(data.get("expires_in", 3600))

        return {
            "access": data["access_token"],
            "refresh": data.get("refresh_token"),
            "expires_in": expires_in,
            "scope": data.get("scope"),
            "token_type": data.get("token_type"),
        }

    def list_calendar_events(
        self,
        *,
        access_token: str,
        calendar_id: str,
        time_min: str,
        time_max: str,
        max_results: int = 100,
    ):
        response = requests.get(
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            params={
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": "true",
                "orderBy": "startTime",
                "maxResults": max_results,
            },
            timeout=30,
        )

        if response.status_code == 401:
            raise PermissionError(f"Google token inválido/expirado: {response.text}")

        if response.status_code != 200:
            raise Exception(f"Falha ao listar eventos do Google Calendar: {response.text}")

        return response.json()

    def refresh_access_token_if_needed(
        self,
        *,
        access_token: str,
        refresh_token: str,
        expires_at: datetime | None,
    ):
        if not refresh_token:
            return {
                "access_token": access_token,
                "expires_at": expires_at,
                "refreshed": False,
            }

        now_utc = datetime.now(timezone.utc)

        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if expires_at > now_utc:
                return {
                    "access_token": access_token,
                    "expires_at": expires_at,
                    "refreshed": False,
                }

        refreshed = self.refresh_access_token(access_token, refresh_token)

        return {
            "access_token": refreshed["access"],
            "expires_at": refreshed["expiry"],
            "refreshed": True,
        }