import requests
from app.core.config import settings


class EvolutionService:
    @staticmethod
    def _headers():
        # Evolution normalmente usa header "apikey"
        return {"apikey": settings.EVOLUTION_API_KEY}

    @staticmethod
    def get_info():
        url = f"{settings.EVOLUTION_BASE_URL.rstrip('/')}/"
        r = requests.get(url, headers=EvolutionService._headers(), timeout=20)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def create_instance(instance_name: str, number: str, qrcode: bool, integration: str):
        url = f"{settings.EVOLUTION_BASE_URL.rstrip('/')}/instance/create"
        payload = {
            "instanceName": instance_name,
            "number": number,
            "qrcode": qrcode,
            "integration": integration,
        }
        r = requests.post(url, json=payload, headers=EvolutionService._headers(), timeout=30)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def connect_instance(instance_name: str):
        url = f"{settings.EVOLUTION_BASE_URL.rstrip('/')}/instance/connect"
        payload = {"instanceName": instance_name}
        r = requests.post(url, json=payload, headers=EvolutionService._headers(), timeout=30)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def connection_state(instance_name: str):
        url = f"{settings.EVOLUTION_BASE_URL.rstrip('/')}/instance/connectionState"
        params = {"instanceName": instance_name}
        r = requests.get(url, params=params, headers=EvolutionService._headers(), timeout=20)
        r.raise_for_status()
        return r.json()
