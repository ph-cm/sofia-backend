from __future__ import annotations

from typing import Any, Dict, Optional
from time import time


class TenantService:
    """
    STUB:
      - Troque isso por leitura no seu banco (ex: Tenant model)
      - E armazene dedup em Redis/DB
    """

    # exemplo em memória (pra teste)
    _TENANTS: Dict[str, Dict[str, Any]] = {
        # "tenant_1": {"chatwoot_account_id": 1, "chatwoot_inbox_id": 2, "chatwoot_api_token": "xxx"}
    }

    # dedup em memória (trocar por Redis)
    _DEDUP: Dict[str, float] = {}  # key -> timestamp
    _DEDUP_TTL_SECONDS = 60 * 10   # 10 min

    @staticmethod
    def get_by_evolution_instance(instance_name: str) -> Optional[Dict[str, Any]]:
        return TenantService._TENANTS.get(instance_name)

    @staticmethod
    def is_duplicate_message(instance_name: str, message_id: str) -> bool:
        TenantService._gc()
        k = f"{instance_name}:{message_id}"
        return k in TenantService._DEDUP

    @staticmethod
    def mark_message_processed(instance_name: str, message_id: str) -> None:
        TenantService._gc()
        k = f"{instance_name}:{message_id}"
        TenantService._DEDUP[k] = time()

    @staticmethod
    def _gc():
        now = time()
        dead = [k for k, ts in TenantService._DEDUP.items() if (now - ts) > TenantService._DEDUP_TTL_SECONDS]
        for k in dead:
            TenantService._DEDUP.pop(k, None)
