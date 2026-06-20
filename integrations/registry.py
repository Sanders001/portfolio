"""
Provider Registry — Registro em memória de adapters com decorator.

Padrão: cada adapter se auto-registra ao ser importado, usando o
decorator @integration_provider("tipo.nome").

Exemplo:
    @integration_provider("payment.stripe")
    class StripeAdapter(IPaymentGateway):
        ...

    @integration_provider("payment.mercadopago")
    class MercadoPagoAdapter(IPaymentGateway):
        ...

Na inicialização, o Discovery importa os módulos dos adapters
e todos se registram automaticamente.
"""
import logging
from typing import Callable, Dict, Type

from .interfaces import IIntegrationProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Registry em memória dos adapters disponíveis.

    Usa um class-level dict para manter o estado global.
    Isso é intencional — o registry deve ser singleton e acessível
    de qualquer ponto do sistema sem injeção de dependência.
    """
    _providers: Dict[str, Type[IIntegrationProvider]] = {}

    @classmethod
    def register(cls, key: str) -> Callable:
        """
        Decorator que registra um adapter no registry.

        Args:
            key: Chave no formato "tipo.nome" (ex: "payment.stripe").

        Returns:
            Decorator que registra a classe e a retorna inalterada.
        """
        def decorator(adapter_class: Type[IIntegrationProvider]):
            if key in cls._providers:
                logger.warning(f"[ProviderRegistry] Overwriting existing provider for key '{key}'")
            cls._providers[key] = adapter_class
            logger.debug(f"[ProviderRegistry] Adapter registered: {key} -> {adapter_class.__name__}")
            return adapter_class
        return decorator

    @classmethod
    def get(cls, key: str) -> Type[IIntegrationProvider]:
        """
        Recupera a classe do adapter pela chave.

        Raises:
            ValueError: Se a chave não estiver registrada.
        """
        adapter = cls._providers.get(key)
        if not adapter:
            raise ValueError(
                f"Provider adapter not found for key '{key}'. "
                f"Was it registered with @integration_provider?"
            )
        return adapter

    @classmethod
    def get_all(cls) -> Dict[str, Type[IIntegrationProvider]]:
        """Retorna todos os providers registrados."""
        return cls._providers.copy()

    @classmethod
    def clear(cls) -> None:
        """Limpa o registry (útil para testes)."""
        cls._providers.clear()


# Alias do decorator para uso mais limpo
integration_provider = ProviderRegistry.register
