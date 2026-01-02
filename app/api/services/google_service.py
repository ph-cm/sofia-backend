from google_auth_oauthlib.flow import Flow
from app.core.config import settings
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from datetime import datetime, timezone

class GoogleAuthService:
    def __init__(self):
        self.client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "project_id": "saas-secretaria",  # opcional
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
            }
        }

        self.scopes = settings.GOOGLE_SCOPES.split(",")

    def create_flow(self):
        flow = Flow.from_client_config(
            client_config=self.client_config,
            scopes=self.scopes
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        return flow

    def auth_url(self, user_id: int):
        flow = self.create_flow()

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            state=str(user_id)
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
            "expiry": creds.expiry
        }
