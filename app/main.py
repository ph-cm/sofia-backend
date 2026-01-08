## ponto de entrada do FastAPI (app instantiation, middlewares, inclusão de rotas)

# app/main.py
from fastapi import FastAPI
from app.core.config import settings

# Importe seus roteadores (endpoints)
from app.api.endpoints import whatsapp, google, users, auth, google_debug, google_calendar, disponibilidade

app = FastAPI(
    title="SaaS Secretaria Inteligente",
    description="Backend para gerenciamento de instâncias e integrações.",
    version="0.1.0",
)

app.include_router(google.router)
app.include_router(auth.router)
app.include_router(google_debug.router)
app.include_router(google_calendar.router)
app.include_router(disponibilidade.router)
# Exemplo: Usando uma variável de configuração
@app.get("/")
def read_root():
    return {"app_name": app.title, "environment": settings.ENV}

# Incluindo as rotas
# app.include_router(users.router, prefix="/api/users", tags=["users"])
# app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["whatsapp"])
# app.include_router(google.router, prefix="/api/google", tags=["google"])

# Para rodar com uvicorn:
# uvicorn app.main:app --reload

#domain de teste: https://nonclaimable-louder-felton.ngrok-free.dev 