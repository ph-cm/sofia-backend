from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi import HTTPException
from app.api.models.user import User
from app.core.security import criar_token

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

        # Cria o token JWT
        token = criar_token({"sub": str(user.id)})

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email
            }
        }
