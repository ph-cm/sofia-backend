## Logica de segurança (jwt, hashing de senha, etc)
from datetime import datetime, timedelta
from jose import jwt
from app.core.config import settings
from fastapi import Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

SECRET_KEY = settings.SECRET_KEY  # Usar do config
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def criar_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    token_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        return {"id": int(user_id)}  # Retorna dict com id
    except:
        raise HTTPException(401, "Token inválido")
    
import os

#Validacao de quem esta chamando
def get_n8n_service(x_n8n_api_key: str = Header(None)):
    if x_n8n_api_key != os.getenv("N8N_API_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized service")
    return True

#verificar senha da n8n
def verify_n8n_api_key(x_api_key: str = Header(...)):
    if not settings.N8N_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="N8N API Key não configurada no servidor"
        )

    if x_api_key != settings.N8N_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key"
        )
        
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)