"""
Resolver — Resolução de provider por tenant com fallback.

Cada tenant pode ter configurações diferentes de providers.
O Resolver consulta as configurações do tenant e instancia o adapter
correto com as credenciais adequadas.

Fluxo:
1. Consulta TenantSettings no banco para obter a key do provider ativo
2. Se não encontrar → usa fallback default
3. Busca a classe do adapter no ProviderRegistry
4. Busca as credenciais do tenant
5. Instancia e retorna o adapter
"""
import logging
from typing import Any, Dict, Optional

from .registry import ProviderRegistry

logger = logging.getLogger(__name__)

# Fallback defaults — usados quando não há config no banco para o tenant.
DEFAULT_PROVIDER_KEYS: Dict[str, str] = {
    "messaging": "messaging.default",
    "email": "email.smtp",
    "payment": "payment.default",
    "shipping": "shipping.default",
}


class ProviderResolver:
    """
    Resolver genérico para instanciar o provedor correto para um Tenant.

    Usa injeção de dependência para obter settings e credenciais,
    mantendo o resolver desacoplado do banco de dados.

    Args:
        settings_loader: Função que recebe (tenant_id, provider_type) e retorna
            a key do provider ativo, ou None para usar default.
        credentials_loader: Função que recebe (tenant_id, provider_type) e retorna
            dict de credenciais.
        defaults: Dict de provider_type → default key. Sobrescreve DEFAULT_PROVIDER_KEYS.
    """

    def __init__(
        self,
        settings_loader: Optional[callable] = None,
        credentials_loader: Optional[callable] = None,
        defaults: Optional[Dict[str, str]] = None,
    ):
        self._settings_loader = settings_loader
        self._credentials_loader = credentials_loader
        self._defaults = defaults or DEFAULT_PROVIDER_KEYS

    def resolve(self, tenant_id: str, provider_type: str) -> Any:
        """
        Resolve e instancia o provider correto para o tenant.

        Args:
            tenant_id: Identificador do tenant.
            provider_type: Tipo de provider (ex: "payment", "messaging").

        Returns:
            Instância do adapter com credenciais aplicadas.
        """
        active_key = self._resolve_provider_key(tenant_id, provider_type)

        logger.debug(
            f"[ProviderResolver] Resolving key '{active_key}' for tenant '{tenant_id}'"
        )

        adapter_class = ProviderRegistry.get(active_key)
        credentials = self._resolve_credentials(tenant_id, provider_type)

        return adapter_class(credentials)

    def _resolve_provider_key(self, tenant_id: str, provider_type: str) -> str:
        """
        Resolve a key do provider ativo.
        Tenta o settings_loader primeiro, depois fallback.
        """
        default_key = self._defaults.get(provider_type, "")

        if self._settings_loader:
            try:
                db_key = self._settings_loader(tenant_id, provider_type)
                if db_key:
                    logger.debug(
                        f"[ProviderResolver] tenant={tenant_id} type={provider_type} → DB key={db_key}"
                    )
                    return db_key
            except Exception as e:
                logger.warning(
                    f"[ProviderResolver] Failed to load settings for tenant={tenant_id} "
                    f"type={provider_type}: {e}. Using fallback '{default_key}'."
                )

        logger.debug(
            f"[ProviderResolver] tenant={tenant_id} type={provider_type} → fallback={default_key}"
        )
        return default_key

    def _resolve_credentials(self, tenant_id: str, provider_type: str) -> Dict[str, Any]:
        """
        Busca as credenciais do tenant para o provider_type.
        Retorna dict vazio se não encontrar.
        """
        if self._credentials_loader:
            try:
                creds = self._credentials_loader(tenant_id, provider_type)
                if creds:
                    return creds
            except Exception as e:
                logger.warning(
                    f"[ProviderResolver] Failed to load credentials for "
                    f"tenant={tenant_id} type={provider_type}: {e}"
                )

        return {}
