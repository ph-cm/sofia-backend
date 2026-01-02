from datetime import datetime, timezone, timedelta
import requests
from sqlalchemy.orm import Session

from app.api.models.google_token import GoogleToken
from app.core.config import settings


class GoogleTokenService:

    @staticmethod
    def get_by_user(db: Session, user_id: int) -> GoogleToken | None:
        return (
            db.query(GoogleToken)
            .filter(GoogleToken.user_id == user_id)
            .first()
        )

    @staticmethod
    def save_tokens(
        db: Session,
        user_id: int,
        access_token: str,
        refresh_token: str,
        expires_in: int | None = None,
        scope: str | None = None,
    ) -> GoogleToken:

        expiry = None
        if expires_in:
            expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        token = GoogleTokenService.get_by_user(db, user_id)

        if token:
            token.google_access_token = access_token
            token.google_refresh_token = refresh_token
            token.google_token_expiry = expiry
            token.scope = scope
        else:
            token = GoogleToken(
                user_id=user_id,
                google_access_token=access_token,
                google_refresh_token=refresh_token,
                google_token_expiry=expiry,
                scope=scope,
            )
            db.add(token)

        db.commit()
        db.refresh(token)
        return token

    @staticmethod
    def refresh_access_token(db: Session, token: GoogleToken) -> GoogleToken:
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": token.google_refresh_token,
                "grant_type": "refresh_token",
            },
        )

        if response.status_code != 200:
            raise Exception(response.text)

        data = response.json()

        token.google_access_token = data["access_token"]
        token.google_token_expiry = datetime.now(timezone.utc) + timedelta(
            seconds=data.get("expires_in", 3600)
        )

        db.commit()
        db.refresh(token)
        return token

    @staticmethod
    def get_valid_access_token(db: Session, user_id: int) -> str:
        token = GoogleTokenService.get_by_user(db, user_id)

        if not token:
            raise Exception("Usuário não conectado ao Google")

        if (
            token.google_token_expiry
            and token.google_token_expiry <= datetime.now(timezone.utc)
        ):
            token = GoogleTokenService.refresh_access_token(db, token)

        return token.google_access_token
