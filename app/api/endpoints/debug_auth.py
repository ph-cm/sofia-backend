from fastapi import APIRouter, Header

router = APIRouter(prefix="/debug", tags=["Debug"])

@router.get("/auth-header")
def debug_auth_header(authorization: str | None = Header(default=None)):
    return {"authorization": authorization}
