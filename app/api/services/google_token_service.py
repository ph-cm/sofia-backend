from datetime import datetime, timezone, timedelta
import requests
from sqlalchemy.orm import Session

from app.api.models.google_token import GoogleToken
from app.core.config import settings


class GoogleTokenNotFound(Exception):
    pass


class GoogleTokenRefreshFailed(Exception):
    pass


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
        refresh_token: str | None,
        expires_in: int | None = None,
        scope: str | None = None,
    ) -> GoogleToken:
        """
        Salva tokens do OAuth.
        IMPORTANTE:
        - Google pode NÃO retornar refresh_token em logins subsequentes.
          Então só atualize refresh_token se ele vier preenchido.
        - expiry deve ser tz-aware (UTC).
        """

        expiry = None
        if expires_in is not None:
            expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

        token = GoogleTokenService.get_by_user(db, user_id)

        if token:
            token.google_access_token = access_token

            # Só sobrescreve refresh_token se vier um novo (não-vazio)
            if refresh_token:
                token.google_refresh_token = refresh_token

            token.google_token_expiry = expiry
            token.scope = scope
        else:
            token = GoogleToken(
                user_id=user_id,
                google_access_token=access_token,
                google_refresh_token=refresh_token or "",
                google_token_expiry=expiry,
                scope=scope,
            )
            db.add(token)

        db.commit()
        db.refresh(token)
        return token

    # =========================
    # LEGADO / COMPARTILHADO
    # NÃO MEXER NO COMPORTAMENTO
    # =========================
    @staticmethod
    def refresh_access_token(db: Session, token: GoogleToken) -> GoogleToken:
        """
        Faz refresh usando refresh_token salvo no banco e atualiza access + expiry.
        Mantido como legado para não quebrar outros processos.
        """
        if not token.google_refresh_token:
            raise GoogleTokenRefreshFailed("Refresh token não existe para este usuário.")

        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": token.google_refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise GoogleTokenRefreshFailed(
                f"Erro ao renovar token Google: {response.text}"
            )

        data = response.json()

        token.google_access_token = data["access_token"]

        expires_in = int(data.get("expires_in", 3600))
        token.google_token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        db.commit()
        db.refresh(token)
        return token

    @staticmethod
    def get_valid_access_token(db: Session, user_id: int) -> str:
        """
        Retorna access token válido.
        Método legado/compartilhado.
        """
        token = GoogleTokenService.get_by_user(db, user_id)
        if not token:
            raise GoogleTokenNotFound("Usuário não conectado ao Google")

        now = datetime.now(timezone.utc)

        if (not token.google_token_expiry) or (token.google_token_expiry <= now):
            token = GoogleTokenService.refresh_access_token(db, token)

        return token.google_access_token

    # =========================
    # NOVO / ISOLADO PARA AGENDA
    # =========================
    @staticmethod
    def refresh_access_token_agenda(db: Session, token: GoogleToken) -> GoogleToken:
        """
        Variante isolada para a Agenda.
        Não altera o comportamento do fluxo legado.
        Em invalid_grant, devolve erro marcado pro front pedir reconnect.
        """
        if not token.google_refresh_token:
            raise GoogleTokenRefreshFailed(
                "google_reauth_required: Refresh token não existe para este usuário."
            )

        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": token.google_refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )

        if response.status_code != 200:
            try:
                payload = response.json()
            except Exception:
                payload = None

            if isinstance(payload, dict) and payload.get("error") == "invalid_grant":
                raise GoogleTokenRefreshFailed(
                    "google_reauth_required: Token do Google expirou ou foi revogado. Reconecte sua conta."
                )

            raise GoogleTokenRefreshFailed(
                f"Erro ao renovar token Google (agenda): {response.text}"
            )

        data = response.json()

        access = data.get("access_token")
        if not access:
            raise GoogleTokenRefreshFailed(
                f"Erro ao renovar token Google (agenda): resposta sem access_token ({data})"
            )

        token.google_access_token = access

        expires_in = int(data.get("expires_in", 3600))
        token.google_token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        db.commit()
        db.refresh(token)
        return token

    @staticmethod
    def get_valid_access_token_agenda(db: Session, user_id: int) -> str:
        token = GoogleTokenService.get_by_user(db, user_id)
        if not token:
            raise GoogleTokenNotFound("Usuário não conectado ao Google")

        now = datetime.now(timezone.utc)
        refresh_threshold = now + timedelta(minutes=2)

        if (not token.google_token_expiry) or (token.google_token_expiry <= refresh_threshold):
            token = GoogleTokenService.refresh_access_token_agenda(db, token)

        return token.google_access_token