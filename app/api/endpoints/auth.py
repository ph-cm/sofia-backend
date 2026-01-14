from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import UserCreate, UserLogin, UserResponse
from app.api.services.auth_service import AuthService
from app.core.security import criar_token
from app.schemas.user import LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = AuthService.authenticate(db, payload.email, payload.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = criar_token({"sub": str(user.id)})

    return LoginResponse(
        access_token=token,
        user=UserOut.from_orm(user)
    )
