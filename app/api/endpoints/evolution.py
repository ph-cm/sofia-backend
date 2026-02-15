from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Any, Dict

from app.core.security import verify_n8n_api_key
from app.api.services.evolution_service import EvolutionService

router = APIRouter(prefix="/evolution", tags=["Evolution"])


# Se quiser travar pra um valor (recomendado pro teu caso):
EvolutionIntegration = Literal["WHATSAPP-BAILEYS"]


class CreateInstanceIn(BaseModel):
    instance_name: str = Field(..., min_length=2, max_length=64, examples=["tenant_1"])
    # número SEM "+" e SEM espaços. Ex: 553499190547
    number: str = Field(..., min_length=10, max_length=20, examples=["553499190547"])
    qrcode: bool = Field(True, examples=[True])
    integration: EvolutionIntegration = Field("WHATSAPP-BAILEYS", examples=["WHATSAPP-BAILEYS"])


class CreateInstanceOut(BaseModel):
    ok: bool
    evolution_raw: Dict[str, Any]


class ConnectOut(BaseModel):
    ok: bool
    instance_name: str
    qrcode: Optional[str] = None
    qrcode_base64: Optional[str] = None
    evolution_raw: Dict[str, Any]

class SetWebhookIn(BaseModel):
    instance_name: str = Field(..., examples=["tenant_1"])
    url: str = Field(..., examples=["https://webhook.site/248aa640-f03f-42d2-abb9-d0779f3918ca"])
    enabled: bool = True
    webhook_by_events: bool = False
    webhook_base64: bool = False
    events: List[str] = Field(default_factory=lambda: ["MESSAGES_UPSERT", "CONNECTION_UPDATE"])

class WebhookOut(BaseModel):
    ok: bool
    instance_name: str
    evolution_raw: Dict[str, Any]

@router.get("/info", dependencies=[Depends(verify_n8n_api_key)])
def evo_info():
    try:
        return EvolutionService.get_info()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution error: {str(e)}")


@router.post("/instances", response_model=CreateInstanceOut, dependencies=[Depends(verify_n8n_api_key)])
def evo_create_instance(payload: CreateInstanceIn):
    try:
        raw = EvolutionService.create_instance(
            instance_name=payload.instance_name,
            number=payload.number,
            qrcode=payload.qrcode,
            integration=payload.integration,
        )
        return {"ok": True, "evolution_raw": raw}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution error: {str(e)}")


from fastapi import Query

@router.post(
    "/instances/{instance_name}/connect",
    response_model=ConnectOut,
    dependencies=[Depends(verify_n8n_api_key)],
)
def evo_connect_instance(
    instance_name: str,
    number: str = Query(..., description="Ex: 553499190547 (sem +)"),
):
    try:
        raw = EvolutionService.connect_instance(instance_name, number)

        # pega o QR da resposta REAL (no seu caso ele vem em raw["qrcode"]["base64"])
        qr_base64 = None
        if isinstance(raw.get("qrcode"), dict):
            qr_base64 = raw["qrcode"].get("base64")
        elif isinstance(raw.get("qrcode"), str):
            qr_base64 = raw.get("qrcode")

        return {
            "ok": True,
            "instance_name": instance_name,
            "qrcode_base64": qr_base64,
            "evolution_raw": raw,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution error: {str(e)}")


@router.get(
    "/instances/{instance_name}/state",
    dependencies=[Depends(verify_n8n_api_key)],
)
def evo_instance_state(instance_name: str):
    try:
        return EvolutionService.connection_state(instance_name)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution error: {str(e)}")

@router.get(
    "/evolution/instances/{instance_name}/qrcode",
    response_model=ConnectOut,
)
def evo_instance_qrcode(instance_name: str):
    """
    Rota salva-vidas: tenta pegar o QRCode em QUALQUER formato possível.
    Funciona mesmo quando o /connect não retorna o QR.
    """
    try:
        raw = EvolutionService.connection_state(instance_name)

        # tenta todos os formatos possíveis
        qrcode = (
            raw.get("qrcode")
            or raw.get("qrCode")
            or raw.get("qr_code")
            or (raw.get("instance") or {}).get("qrcode")
            or (raw.get("instance") or {}).get("qrCode")
        )

        qrcode_base64 = (
            raw.get("qrcode_base64")
            or raw.get("qrCodeBase64")
            or (raw.get("instance") or {}).get("qrcode_base64")
            or (raw.get("instance") or {}).get("qrCodeBase64")
        )

        return {
            "ok": True,
            "instance_name": instance_name,
            "qrcode": qrcode if isinstance(qrcode, str) else None,
            "qrcode_base64": qrcode_base64 if isinstance(qrcode_base64, str) else None,
            "evolution_raw": raw,
        }

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution error: {str(e)}")

@router.get(
    "/instances/{instance_name}/status",
    response_model=ConnectOut,
    dependencies=[Depends(verify_n8n_api_key)],
)
def evo_instance_status(instance_name: str):
    """
    Endpoint de diagnóstico geral da instância Evolution.
    Tenta recuperar QRCode + status + detalhes internos, independentemente
    do formato retornado pelo Evolution.
    """
    try:
        raw = EvolutionService.connection_state(instance_name)

        instance = raw.get("instance") or raw

        # --- Possíveis chaves de QRCode ---
        qrcode = (
            raw.get("qrcode")
            or raw.get("qrCode")
            or raw.get("qr_code")
            or instance.get("qrcode")
            or instance.get("qrCode")
            or instance.get("qr_code")
        )

        qrcode_base64 = (
            raw.get("qrcode_base64")
            or raw.get("qrCodeBase64")
            or instance.get("qrcode_base64")
            or instance.get("qrCodeBase64")
        )

        # --- Status da instância ---
        state = (
            instance.get("state")
            or instance.get("status")
            or raw.get("state")
            or raw.get("status")
        )

        # --- Outros dados úteis ---
        retries = (
            instance.get("retries")
            or raw.get("retries")
        )

        fail_reason = (
            instance.get("failReason")
            or instance.get("failureReason")
            or raw.get("failReason")
            or raw.get("failureReason")
        )

        phone_connected = (
            instance.get("phone_connected")
            or instance.get("phoneConnected")
            or raw.get("phone_connected")
            or raw.get("phoneConnected")
        )

        return {
            "ok": True,
            "instance_name": instance_name,
            "state": state,
            "retries": retries,
            "fail_reason": fail_reason,
            "phone_connected": phone_connected,
            "qrcode": qrcode if isinstance(qrcode, str) else None,
            "qrcode_base64": qrcode_base64 if isinstance(qrcode_base64, str) else None,
            "evolution_raw": raw,
        }

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution error: {str(e)}")


@router.post("/instances/{instance_name}/restart", dependencies=[Depends(verify_n8n_api_key)])
def evo_restart_instance(instance_name: str):
    try:
        return EvolutionService.restart_instance(instance_name)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution error: {str(e)}")


@router.post("/webhook/set", dependencies=[Depends(verify_n8n_api_key)])
def evo_webhook_set(payload: SetWebhookIn):
    try:
        raw = EvolutionService.set_webhook(
            instance_name=payload.instance_name,
            url=payload.url,
            events=payload.events,
            enabled=payload.enabled,
            webhook_by_events=payload.webhook_by_events,
            webhook_base64=payload.webhook_base64,
        )
        return {"ok": True, "instance_name": payload.instance_name, "evolution_raw": raw}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution error: {str(e)}")


@router.get("/webhook/find/{instance_name}", response_model=WebhookOut, dependencies=[Depends(verify_n8n_api_key)])
def evo_webhook_find(instance_name: str):
    try:
        raw = EvolutionService.find_webhook(instance_name=instance_name)
        return {"ok": True, "instance_name": instance_name, "evolution_raw": raw}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution error: {str(e)}")

