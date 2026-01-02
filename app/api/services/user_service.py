## logica de negocios para usuários(CRUD))from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut, UserLogin
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.api.models.user import User
from app.api.models.google_token import GoogleToken

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:

    @staticmethod
    def create_user(db: Session, data: UserCreate):
        hashed = pwd.hash(data.password)
        user = User(email=data.email, password_hash=hashed)
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
    def save_google_tokens(db: Session, user_id: int, access: str, refresh: str):
        user = db.get(User, user_id)
        user.google_access_token = access
        user.google_refresh_token = refresh
        db.commit()
        return user
    
    @staticmethod
    def update_google_access_token(db, user_id, access, expiry):
        token = db.query(GoogleToken).filter_by(user_id=user_id).first()
        token.google_access_token = access
        token.google_token_expiry = expiry
        db.commit()
        
    @staticmethod
    def get_google_tokens(db, user_id: int):
        return (
            db.query(GoogleToken)
            .filter(GoogleToken.user_id == user_id)
            .first()
        )

