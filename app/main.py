## ponto de entrada do FastAPI (app instantiation, middlewares, inclusão de rotas)

# app/main.py
from fastapi import FastAPI
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware

# Importe seus roteadores (endpoints)
from app.api.endpoints import google,  auth, google_debug, disponibilidade, google_calendar_availability, google_calendar_events, conversation_context, resolve_user, users, tenants, appointments, google_calendar_mirror, tenant_integration
from app.api.endpoints import debug_auth
from app.api.endpoints import tenant_provision
from app.api.endpoints import evolution
from app.api.endpoints import evolution_webhooks
from app.api.endpoints import tenant_evolution
from app.api.endpoints import chatwoot_provisioning

app = FastAPI(
    title="SaaS Secretaria Inteligente",
    description="Backend para gerenciamento de instâncias e integrações.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(google.router)
app.include_router(auth.router)
app.include_router(google_debug.router)
app.include_router(disponibilidade.router)
app.include_router(google_calendar_availability.router)
app.include_router(google_calendar_events.router)
app.include_router(conversation_context.router)
app.include_router(resolve_user.router)
app.include_router(users.router)
app.include_router(tenants.router)
app.include_router(appointments.router)
app.include_router(google_calendar_mirror.router)
app.include_router(tenant_integration.router)
app.include_router(debug_auth.router)
app.include_router(tenant_provision.router)
app.include_router(evolution.router)
app.include_router(evolution_webhooks.router)
app.include_router(tenant_evolution.router)
app.include_router(chatwoot_provisioning.router)

# Exemplo: Usando uma variável de configuração
@app.get("/")
def read_root():
    return {"app_name": app.title, "environment": settings.ENV}

import logging, re
logger = logging.getLogger("startup")

@app.on_event("startup")
def startup_log():
    from app.core.config import settings
    safe = re.sub(r":([^:@/]+)@", ":***@", settings.DATABASE_URL)
    logger.warning("STARTUP DATABASE_URL = %s", safe)

# Incluindo as rotas
# app.include_router(users.router, prefix="/api/users", tags=["users"])
# app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["whatsapp"])
# app.include_router(google.router, prefix="/api/google", tags=["google"])

# Para rodar com uvicorn:
# uvicorn app.main:app --reload

#domain de teste: https://nonclaimable-louder-felton.ngrok-free.dev 