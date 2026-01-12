# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session

# from app.db.session import get_db
# from app.api.services.google_token_service import GoogleTokenService
# from app.api.services.google_calendar_service import list_calendars
# from app.api.models.google_token import GoogleToken

# router = APIRouter(prefix="/google/test", tags=["google-calendar"])

# @router.get("/calendars")
# def test_list_calendars(user_id: int, db: Session = Depends(get_db)):
#     token = GoogleTokenService.get_by_user(db, user_id)

#     if not token:
#         raise HTTPException(404, "Usuário não conectado ao Google")

#     try:
#         return list_calendars(db, token)
#     except Exception as e:
#         raise HTTPException(500, str(e))

