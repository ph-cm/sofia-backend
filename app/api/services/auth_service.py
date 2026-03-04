from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi import HTTPException
from app.api.models.user import User
from app.core.security import criar_token
from app.api.models.tenant import Tenant # Ajuste o caminho conforme o seu projeto

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:

    @staticmethod
    def create_user(db: Session, email: str, password: str):
        # bcrypt: limite de 72 BYTES
        password_bytes = password.encode("utf-8")

        if len(password_bytes) > 72:
            raise ValueError("Senha muito longa (máx. 72 bytes)")

        password_hash = pwd.hash(password)

        user = User(
            email=email,
            password_hash=password_hash
        )
        print("🔥🔥🔥 AUTH SERVICE VERSION 2026-01-02 🔥🔥🔥")
        print("PASSWORD RECEIVED:", password)
        print("LEN BYTES:", len(password.encode("utf-8")))

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def authenticate(db: Session, email: str, password: str):
        user = db.query(User).filter(User.email == email).first()

        if not user:
            return None

        if not pwd.verify(password, user.password_hash):
            return None

        return user

    @staticmethod
    def login(db: Session, email: str, password: str):
        user = AuthService.authenticate(db, email, password)

        if not user:
            raise HTTPException(status_code=400, detail="Email ou senha incorretos")

        # 1. Buscar o tenant associado a este usuário.
        # Supondo que a tabela tenants tenha uma coluna 'user_id' que liga o dono ao tenant:
        tenant = db.query(Tenant).filter(Tenant.user_id == user.id).first()
        
        # Se você usar relationships do SQLAlchemy (ex: user.tenant), poderia ser apenas:
        # tenant_id = user.tenant.id if user.tenant else None
        
        tenant_id = tenant.id if tenant else None

        # 2. Injetar o tenant_id no Token JWT
        token = criar_token({
            "sub": str(user.id),
            "tenant_id": tenant_id
        })

        # 3. Retornar todos os dados que o seu frontend já espera, AGORA com o tenant_id
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "nome": user.nome,
                "phone_channel": getattr(user, "phone_channel", None),
                "calendar_id": getattr(user, "calendar_id", None),
                "timezone": getattr(user, "timezone", None),
                "duracao_consulta": getattr(user, "duracao_consulta", None),
                "valor_consulta": getattr(user, "valor_consulta", None),
                "ativo": getattr(user, "ativo", True),
                "inbox_id": getattr(user, "inbox_id", None),
                "tenant_id": tenant_id  # <-- Agora ele vai aparecer no LocalStorage!
            }
        }
