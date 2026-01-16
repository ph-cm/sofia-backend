## Rotas (endpoints) para Usuários/Auth (ex: /register, /login)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import UserCreate, UserLogin, UserOut, UserUpdate
from app.api.services.user_service import UserService
from app.api.models.user import User
from app.core.security import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    created = UserService.create_user(db, user)
    return created


@router.post("/login", response_model=UserOut)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = UserService.authenticate(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user

@router.put("/update/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    data = payload.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user

