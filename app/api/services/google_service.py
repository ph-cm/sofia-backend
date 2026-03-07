from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from app.core.config import settings

from datetime import datetime, timezone
from urllib.parse import urlencode
import requests


class GoogleAuthService:
    def __init__(self):
        self.client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "project_id": "saas-secretaria",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uris": [
                    settings.GOOGLE_REDIRECT_URI,
                    settings.GOOGLE_REDIRECT_URI_AGENDA,
                ],
            }
        }

        self.scopes = settings.GOOGLE_SCOPES.split(",")

    # =========================
    # LEGADO / COMPARTILHADO
    # NÃO MEXER
    # =========================
    def create_flow(self):
        flow = Flow.from_client_config(
            client_config=self.client_config,
            scopes=self.scopes,
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        return flow

    def auth_url(self, user_id: int):
        flow = self.create_flow()

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            state=str(user_id),
        )

        return auth_url

    def exchange_code(self, code: str):
        flow = self.create_flow()
        flow.fetch_token(code=code)

        credentials = flow.credentials

        expiry = credentials.expiry
        if expiry and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        expires_in = None
        if expiry:
            expires_in = int((expiry - datetime.now(timezone.utc)).total_seconds())

        return {
            "access": credentials.token,
            "refresh": credentials.refresh_token,
            "expiry": expiry,
            "expires_in": expires_in,
            "scope": " ".join(credentials.scopes) if credentials.scopes else None,
            "token_type": credentials.token_uri and "Bearer",
        }

    def refresh_access_token(self, access_token: str, refresh_token: str):
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
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