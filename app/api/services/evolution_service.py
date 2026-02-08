# app/api/services/evolution_service.py
from __future__ import annotations

import requests
from typing import Any, Dict, List, Optional
from app.core.config import settings


class EvolutionService:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = (base_url or settings.EVOLUTION_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.EVOLUTION_API_KEY

    def _headers(self) -> Dict[str, str]:
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    def _post(self, path: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            r = requests.post(url, json=payload, headers=self._headers(), timeout=timeout)
            
            # Se for 404 ou 405 (Method Not Allowed), lançamos exceção específica para permitir fallback
            if r.status_code in (404, 405):
                raise FileNotFoundError(f"{r.status_code} Not Found/Method: {url}")
            
            # Se for erro de aplicação (400, 401, 500)
            if r.status_code >= 400:
                try:
                    error_data = r.json()
                except:
                    error_data = r.text
                raise RuntimeError(f"Evolution API Error {r.status_code}: {error_data}")
                
            return r.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Evolution Connection Error: {str(e)}")
    
    def _get(self, path: str, params: Dict[str, Any] = None, timeout: int = 20) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            r = requests.get(url, params=params, headers=self._headers(), timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Evolution Connection Error: {str(e)}")

    # ======================
    # Instance Management
    # ======================

    @staticmethod
    def create_instance(instance_name: str, number: str, qrcode: bool, integration: str):
        svc = EvolutionService()
        return svc._post("/instance/create", {
            "instanceName": instance_name,
            "number": number,
            "qrcode": qrcode,
            "integration": integration,
        })

    @staticmethod
    def connect_instance(instance_name: str, number: str):
        svc = EvolutionService()
        return svc._get(f"/instance/connect/{instance_name}", params={"number": number})

    @staticmethod
    def connection_state(instance_name: str):
        svc = EvolutionService()
        return svc._get(f"/instance/connectionState/{instance_name}")
    
    @staticmethod
    def restart_instance(instance_name: str):
        svc = EvolutionService()
        return svc._post(f"/instance/restart/{instance_name}", {})

    # ======================
    # Webhooks
    # ======================

    @staticmethod
    def set_webhook(
        instance_name: str,
        url: str,
        events: list[str],
        enabled: bool = True,
        webhook_by_events: bool = False,
        webhook_base64: bool = False,
    ):
        svc = EvolutionService()
        payload = {
            "enabled": enabled,
            "url": url,
            "webhook_by_events": webhook_by_events,
            "webhook_base64": webhook_base64,
            "events": events,
        }
        try:
            return svc._post(f"/webhook/set/{instance_name}", payload)
        except FileNotFoundError:
            try:
                return svc._post(f"/webhook/instance/{instance_name}", payload)
            except FileNotFoundError:
                # Fallback Query Param
                return svc._post(f"/webhook/instance?instanceName={instance_name}", payload)

    @staticmethod
    def find_webhook(instance_name: str):
        svc = EvolutionService()
        return svc._get(f"/webhook/find/{instance_name}")

    # ======================
    # Messaging (Estratégia Tripla)
    # ======================

    @classmethod
    def send_text(cls, instance_name: str, to_number: str, text: str):
        svc = cls()
        payload = {
            "number": to_number,
            "text": text,
            "delay": 1200,
            "linkPreview": True
        }
        
        # 1. Tenta V1 (Padrão: /message/sendText/{instance})
        try:
            return svc._post(f"/message/sendText/{instance_name}", payload)
        except FileNotFoundError:
            pass # Tenta próxima estratégia

        # 2. Tenta V2 (Novo Padrão: /message/send/text/{instance})
        try:
            return svc._post(f"/message/send/text/{instance_name}", payload)
        except FileNotFoundError:
            pass # Tenta próxima estratégia

        # 3. Tenta Legacy/QueryParam (/message/sendText?instanceName={instance})
        # Algumas versões exigem isso
        return svc._post(f"/message/sendText?instanceName={instance_name}", payload)

    @classmethod
    def send_audio(cls, instance_name: str, to_number: str, audio_url: str):
        svc = cls()
        
        # Payload comum
        payload = {
            "number": to_number,
            "audio": audio_url,
            "delay": 1200,
            "recordinAudio": True 
        }
        
        # 1. Tenta V1 (/message/sendWhatsAppAudio/{instance})
        try:
            return svc._post(f"/message/sendWhatsAppAudio/{instance_name}", payload)
        except FileNotFoundError:
            pass

        # 2. Tenta V1 Alternativa (/message/sendAudio/{instance})
        try:
            return svc._post(f"/message/sendAudio/{instance_name}", payload)
        except FileNotFoundError:
            pass
            
        # 3. Tenta V2 (/message/send/audio/{instance})
        try:
            return svc._post(f"/message/send/audio/{instance_name}", payload)
        except FileNotFoundError:
            pass

        # 4. Tenta Legacy/QueryParam
        return svc._post(f"/message/sendWhatsAppAudio?instanceName={instance_name}", payload)

    @classmethod
    def send_audio_url(cls, instance_name: str, to: str, audio_url: str, ptt: bool = True):
        return cls.send_audio(instance_name, to, audio_url)