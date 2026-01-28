from typing import Dict, Any


class EvolutionWebhookService:
    @staticmethod
    def handle_event(payload: Dict[str, Any]):
        """
        Centraliza o tratamento do webhook.
        Aqui entra regra de negócio.
        """

        instance = payload.get("instance") or payload.get("instanceName")
        event = payload.get("event") or payload.get("type")

        if not instance or not event:
            return

        match event:
            case "MESSAGES_UPSERT":
                EvolutionWebhookService._handle_message(payload)
            case "CONNECTION_UPDATE":
                EvolutionWebhookService._handle_connection(payload)
            case _:
                print(f"ℹ️ Evento ignorado: {event}")

    @staticmethod
    def _handle_message(payload: Dict[str, Any]):
        print("📩 Mensagem recebida")
        # aqui depois você:
        # - salva
        # - manda pro n8n
        # - manda pro chatwoot

    @staticmethod
    def _handle_connection(payload: Dict[str, Any]):
        print("🔌 Status de conexão atualizado")
