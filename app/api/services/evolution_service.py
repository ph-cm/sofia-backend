# app/api/services/evolution_service.py
from __future__ import annotations

import requests
from typing import Any, Dict, List, Optional
from app.core.config import settings


class EvolutionService:
    def __init__(self, base_url: str = None, api_key: str = None):
        # Permite instanciar com credenciais específicas ou usar as do settings
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
            
            # Se a rota V1 falhar com 404, não levanta erro imediatamente se pudermos tentar V2
            # Mas aqui vamos assumir que o método chamador decide a estratégia
            if r.status_code >= 400:
                # Retorna o erro para ser tratado ou logado
                # Se for 404, lançamos uma exception específica para permitir fallback
                if r.status_code == 404:
                    raise FileNotFoundError(f"404 Not Found: {url}")
                
                # Outros erros (400, 401, 500)
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
        # Método estático mantido para compatibilidade, mas idealmente use instância
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
        # Tenta rota padrão V1/V2 (geralmente é /webhook/set/{instance} ou /webhook/instance/{instance})
        try:
            return svc._post(f"/webhook/set/{instance_name}", payload)
        except FileNotFoundError:
            # Fallback para rota alternativa comum
            return svc._post(f"/webhook/instance/{instance_name}", payload)

    @staticmethod
    def find_webhook(instance_name: str):
        svc = EvolutionService()
        try:
            return svc._get(f"/webhook/find/{instance_name}")
        except Exception:
            # Tenta rota alternativa
            return svc._get(f"/webhook/instance/{instance_name}")

    # ======================
    # Messaging (Refatorado para V1 e V2)
    # ======================

    @classmethod
    def send_text(cls, instance_name: str, to_number: str, text: str):
        svc = cls()  # Cria instância se chamado estaticamente
        payload = {
            "number": to_number,
            "text": text,
            "delay": 1200,
            "linkPreview": True
        }
        
        # Estratégia de Fallback: V1 -> V2
        try:
            # Tenta V1 (mais comum nas instalações atuais)
            return svc._post(f"/message/sendText/{instance_name}", payload)
        except FileNotFoundError:
            # Tenta V2 (padrão novo)
            return svc._post(f"/message/send/text/{instance_name}", payload)

    @classmethod
    def send_audio(cls, instance_name: str, to_number: str, audio_url: str):
        svc = cls()
        
        # Payload V1
        payload_v1 = {
            "number": to_number,
            "audio": audio_url,
            "delay": 1200
        }
        
        try:
            # Tenta V1 (/message/sendWhatsAppAudio ou /message/sendAudio)
            try:
                return svc._post(f"/message/sendWhatsAppAudio/{instance_name}", payload_v1)
            except FileNotFoundError:
                return svc._post(f"/message/sendAudio/{instance_name}", payload_v1)
                
        except FileNotFoundError:
            # Tenta V2
            payload_v2 = {
                "number": to_number,
                "audio": audio_url,
                "recordinAudio": True, # Força aparecer como gravado na hora
                "delay": 1200
            }
            return svc._post(f"/message/send/audio/{instance_name}", payload_v2)

    @classmethod
    def send_audio_url(cls, instance_name: str, to: str, audio_url: str, ptt: bool = True):
        """
        Alias para compatibilidade. O Evolution já lida com URLs em send_audio.
        """
        return cls.send_audio(instance_name, to, audio_url)