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
            
            if r.status_code in (404, 405):
                # Tenta extrair a mensagem de erro para decisão inteligente
                try:
                    resp_json = r.json()
                    # Verifica padrões comuns de erro da Evolution
                    err_response = resp_json.get("response", {})
                    msg_list = err_response.get("message", []) if isinstance(err_response, dict) else []
                    error_msg = str(resp_json)
                    
                    # Se for "Cannot POST", é erro de ROTA (URL errada) -> Devemos tentar outra estratégia
                    is_route_error = "Cannot POST" in error_msg or "Cannot POST" in str(msg_list)
                    
                    # Se for "Instance not found", a rota existe mas o nome tá errado -> NÃO adianta tentar outra rota
                    is_instance_error = "Instance not found" in error_msg or "instance not found" in error_msg.lower()

                    if is_instance_error:
                        raise RuntimeError(f"INSTANCE_NOT_FOUND: A instância '{url.split('/')[-1]}' não existe ou está offline.")

                except RuntimeError:
                    raise # Repassa o erro de instância encontrado
                except:
                    # Se não der pra ler JSON (ex: Nginx HTML), assume erro de rota
                    is_route_error = True

                # Lança FileNotFoundError apenas se for erro de ROTA, para o fallback funcionar
                print(f"DEBUG_EVO_FAIL: {r.status_code} em {path} -> {r.text[:200]}") # Debug visual
                raise FileNotFoundError(f"{r.status_code} Not Found: {url}")
            
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
    def set_webhook(instance_name: str, url: str, events: list[str], enabled: bool = True, webhook_by_events: bool = False, webhook_base64: bool = False):
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
                return svc._post(f"/webhook/instance?instanceName={instance_name}", payload)

    @staticmethod
    def find_webhook(instance_name: str):
        svc = EvolutionService()
        return svc._get(f"/webhook/find/{instance_name}")

    # ======================
    # Messaging (Estratégia "Smart Fallback")
    # ======================

    @classmethod
    def send_text(cls, instance_name: str, to_number: str, text: str):
        svc = cls()
        instance_name = instance_name.strip() # Sanitização básica
        
        payload = {
            "number": to_number,
            "text": text,
            "delay": 1200,
            "linkPreview": True
        }
        
        # 1. Tenta V2 Padrão (/message/send/text/{instance})
        try:
            return svc._post(f"/message/send/text/{instance_name}", payload)
        except FileNotFoundError: pass

        # 2. Tenta V2 API Prefix (/api/message/send/text/{instance})
        try:
            return svc._post(f"/api/message/send/text/{instance_name}", payload)
        except FileNotFoundError: pass

        # 3. Tenta V1 Padrão (/message/sendText/{instance})
        try:
            return svc._post(f"/message/sendText/{instance_name}", payload)
        except FileNotFoundError: pass
        
        # 4. Tenta V1 API Prefix (/api/message/sendText/{instance})
        try:
            return svc._post(f"/api/message/sendText/{instance_name}", payload)
        except FileNotFoundError: pass

        # 5. Tenta Legacy Query Param
        return svc._post(f"/message/sendText?instanceName={instance_name}", payload)

    @classmethod
    def send_audio(cls, instance_name: str, to_number: str, audio_url: str):
        svc = cls()
        instance_name = instance_name.strip()
        
        payload = {
            "number": to_number,
            "audio": audio_url,
            "delay": 1200,
            "recordinAudio": True 
        }
        
        # Tenta sequência de rotas (V2 -> V2API -> V1 -> V1API -> Legacy)
        routes = [
            f"/message/send/audio/{instance_name}",
            f"/api/message/send/audio/{instance_name}",
            f"/message/sendWhatsAppAudio/{instance_name}",
            f"/message/sendAudio/{instance_name}",
            f"/message/sendWhatsAppAudio?instanceName={instance_name}"
        ]
        
        last_error = None
        for route in routes:
            try:
                return svc._post(route, payload)
            except FileNotFoundError as e:
                last_error = e
                continue
        
        raise last_error

    @classmethod
    def send_audio_url(cls, instance_name: str, to: str, audio_url: str, ptt: bool = True):
        return cls.send_audio(instance_name, to, audio_url)