from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import verify_n8n_api_key
from app.api.services.evolution_service import EvolutionService

router = APIRouter(prefix="/evolution", tags=["Evolution"])

class CreateInstanceIn(BaseModel):
    instance_name: str

@router.get("/info", dependencies=[Depends(verify_n8n_api_key)])
def evo_info():
    try:
        return EvolutionService.get_info()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution error: {str(e)}")

@router.post("/instances", dependencies=[Depends(verify_n8n_api_key)])
def evo_create_instance(payload: CreateInstanceIn):
    try:
        return EvolutionService.create_instance(payload.instance_name)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution error: {str(e)}")

@router.post("/instances/{instance_name}/connect", dependencies=[Depends(verify_n8n_api_key)])
def evo_connect_instance(instance_name: str):
    try:
        return EvolutionService.connect_instance(instance_name)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution error: {str(e)}")

@router.get("/instances/{instance_name}/state", dependencies=[Depends(verify_n8n_api_key)])
def evo_instance_state(instance_name: str):
    try:
        return EvolutionService.connection_state(instance_name)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution error: {str(e)}")
