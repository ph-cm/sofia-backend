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
    def connect_instance(instance_name: str, number: str):
        url = f"{settings.EVOLUTION_BASE_URL.rstrip('/')}/instance/connect/{instance_name}"
        params = {"number": number}
        r = requests.get(url, params=params, headers=EvolutionService._headers(), timeout=30)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def connection_state(instance_name: str):
        url = f"{settings.EVOLUTION_BASE_URL.rstrip('/')}/instance/connectionState/{instance_name}"
        r = requests.get(url, headers=EvolutionService._headers(), timeout=20)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def restart_instance(instance_name: str):
        url = f"{settings.EVOLUTION_BASE_URL.rstrip('/')}/instance/restart/{instance_name}"
        r = requests.post(url, headers=EvolutionService._headers(), timeout=30)
        r.raise_for_status()
        return r.json()


    @staticmethod
    def _headers():
        return {"apikey": settings.EVOLUTION_API_KEY}

    @staticmethod
    def _base():
        return settings.EVOLUTION_BASE_URL.rstrip("/")

    @staticmethod
    def _try_post(paths: list[str], json: dict, timeout: int = 30):
        last_exc = None
        for p in paths:
            url = f"{EvolutionService._base()}{p}"
            try:
                r = requests.post(url, json=json, headers=EvolutionService._headers(), timeout=timeout)
                # se for 404/405 tenta o próximo
                if r.status_code in (404, 405):
                    last_exc = Exception(f"{r.status_code} for {url}: {r.text[:300]}")
                    continue
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last_exc = e
                continue
        raise last_exc or Exception("No webhook endpoint matched")

    @staticmethod
    def _try_get(paths: list[str], params: dict | None = None, timeout: int = 20):
        last_exc = None
        for p in paths:
            url = f"{EvolutionService._base()}{p}"
            try:
                r = requests.get(url, params=params, headers=EvolutionService._headers(), timeout=timeout)
                if r.status_code in (404, 405):
                    last_exc = Exception(f"{r.status_code} for {url}: {r.text[:300]}")
                    continue
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last_exc = e
                continue
        raise last_exc or Exception("No webhook endpoint matched")

    @staticmethod
    def set_webhook(instance_name: str, url: str, events: list[str], enabled: bool = True,
                    webhook_by_events: bool = False, webhook_base64: bool = False):
        # ✅ payload conforme docs v2
        payload = {
            "enabled": enabled,
            "url": url,
            "webhook_by_events": webhook_by_events,
            "webhook_base64": webhook_base64,
            "events": events,
        }

        # ✅ endpoint correto no v2: POST /webhook/instance
        candidate_paths = [
            f"/webhook/instance/{instance_name}",                 # alguns builds fazem assim
            "/webhook/instance",                                  # docs v2 mostram esse
            "/webhook/instance?instanceName=" + instance_name,    # fallback
        ]

        return EvolutionService._try_post(candidate_paths, json=payload, timeout=30)

    @staticmethod
    def find_webhook(instance_name: str):
        # ✅ docs v2: GET /webhook/find/[instance]
        candidate_paths = [
            f"/webhook/find/{instance_name}",
            "/webhook/find",  # fallback (se existir) usando query
        ]
        return EvolutionService._try_get(candidate_paths, params={"instanceName": instance_name}, timeout=20)


