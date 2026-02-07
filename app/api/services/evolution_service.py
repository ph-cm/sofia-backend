# app/api/services/evolution_service.py
from __future__ import annotations

import requests
from typing import Any, Dict, Optional, List
from app.core.config import settings


class EvolutionService:
    # ======================
    # Base helpers (únicos)
    # ======================

    @staticmethod
    def _headers() -> Dict[str, str]:
        return {"apikey": settings.EVOLUTION_API_KEY, "Content-Type": "application/json"}

    @staticmethod
    def _base() -> str:
        return settings.EVOLUTION_BASE_URL.rstrip("/")

    @staticmethod
    def _try_post(paths: List[str], json: dict, timeout: int = 30):
        last_exc: Exception | None = None
        for p in paths:
            url = f"{EvolutionService._base()}{p}"
            try:
                r = requests.post(url, json=json, headers=EvolutionService._headers(), timeout=timeout)
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
    def _try_get(paths: List[str], params: dict | None = None, timeout: int = 20):
        last_exc: Exception | None = None
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

    # ======================
    # Existing methods
    # ======================

    @staticmethod
    def get_info():
        url = f"{EvolutionService._base()}/"
        r = requests.get(url, headers=EvolutionService._headers(), timeout=20)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def create_instance(instance_name: str, number: str, qrcode: bool, integration: str):
        url = f"{EvolutionService._base()}/instance/create"
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
        url = f"{EvolutionService._base()}/instance/connect/{instance_name}"
        params = {"number": number}
        r = requests.get(url, params=params, headers=EvolutionService._headers(), timeout=30)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def connection_state(instance_name: str):
        url = f"{EvolutionService._base()}/instance/connectionState/{instance_name}"
        r = requests.get(url, headers=EvolutionService._headers(), timeout=20)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def restart_instance(instance_name: str):
        url = f"{EvolutionService._base()}/instance/restart/{instance_name}"
        r = requests.post(url, headers=EvolutionService._headers(), timeout=30)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def set_webhook(
        instance_name: str,
        url: str,
        events: list[str],
        enabled: bool = True,
        webhook_by_events: bool = False,
        webhook_base64: bool = False,
    ):
        payload = {
            "enabled": enabled,
            "url": url,
            "webhook_by_events": webhook_by_events,
            "webhook_base64": webhook_base64,
            "events": events,
        }

        candidate_paths = [
            f"/webhook/instance/{instance_name}",
            "/webhook/instance",
            "/webhook/instance?instanceName=" + instance_name,
        ]

        return EvolutionService._try_post(candidate_paths, json=payload, timeout=30)

    @staticmethod
    def find_webhook(instance_name: str):
        candidate_paths = [
            f"/webhook/find/{instance_name}",
            "/webhook/find",
        ]
        return EvolutionService._try_get(candidate_paths, params={"instanceName": instance_name}, timeout=20)

    # ======================
    # ✅ NEW: sending methods (outgoing)
    # ======================

    @staticmethod
    def send_text(instance_name: str, number_digits: str, text: str):
        """
        Envia texto para um número.
        number_digits: ex '553491757669'
        """
        payload = {
            "number": number_digits,
            "text": text,
        }

        # Variam por build do Evolution:
        candidate_paths = [
            f"/message/sendText/{instance_name}",
            f"/message/sendText/{instance_name}/",   # alguns servers são chatos com slash
            "/message/sendText",                    # fallback (se aceitar instanceName no body)
        ]

        # fallback extra: se build exigir instanceName no body
        try_payload = dict(payload)
        try_payload["instanceName"] = instance_name

        try:
            return EvolutionService._try_post(candidate_paths[:2], json=payload, timeout=30)
        except Exception:
            return EvolutionService._try_post(candidate_paths[2:], json=try_payload, timeout=30)

    @staticmethod
    def send_audio_url(instance_name: str, number_digits: str, audio_url: str, ptt: bool = False):
        """
        Envia áudio via URL (Evolution baixa a URL).
        """
        payload = {
            "number": number_digits,
            "audio": audio_url,
            "ptt": bool(ptt),
        }

        candidate_paths = [
            f"/message/sendAudio/{instance_name}",
            f"/message/sendAudio/{instance_name}/",
            "/message/sendAudio",
        ]

        try_payload = dict(payload)
        try_payload["instanceName"] = instance_name

        try:
            return EvolutionService._try_post(candidate_paths[:2], json=payload, timeout=60)
        except Exception:
            return EvolutionService._try_post(candidate_paths[2:], json=try_payload, timeout=60)
