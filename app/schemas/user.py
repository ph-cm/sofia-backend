from pydantic import BaseModel, EmailStr
from typing import Optional

# =========================
# Cadastro de usuário (médico)
# =========================
class UserCreate(BaseModel):
    email: EmailStr
    password: str

    nome: Optional[str] = None

    # contato do médico (opcional, administrativo)
    phone_channel: Optional[str] = None  

    # chave operacional
    inbox_id: Optional[int] = None

    calendar_id: Optional[str] = "primary"
    timezone: Optional[str] = "America/Sao_Paulo"
    duracao_consulta: Optional[int] = 60
    valor_consulta: Optional[int] = 0
    ativo: Optional[bool] = True



# =========================
# Login (inalterado)
# =========================
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# =========================
# Retorno de usuário
# =========================
class UserOut(BaseModel):
    id: int
    email: EmailStr

    # 🔽 dados do médico retornáveis
    nome: Optional[str] = None
    phone_channel: Optional[str] = None
    calendar_id: Optional[str] = None
    timezone: Optional[str] = None
    duracao_consulta: Optional[int] = None
    valor_consulta: Optional[int] = None
    ativo: Optional[bool] = None
    inbox_id: Optional[int] = None


    class Config:
        from_attributes = True


# =========================
# Resposta de login (inalterada estruturalmente)
# =========================
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class UserUpdate(BaseModel):
    nome: Optional[str] = None
    phone_channel: Optional[str] = None
    calendar_id: Optional[str] = None
    timezone: Optional[str] = None
    duracao_consulta: Optional[int] = None
    valor_consulta: Optional[float] = None
    ativo: Optional[bool] = None