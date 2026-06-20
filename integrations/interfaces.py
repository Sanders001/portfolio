"""
Interfaces (Ports) — Contratos abstratos para integrações externas.

Cada interface define o contrato que qualquer adapter (provedor)
deve implementar. Isso permite trocar provedores sem alterar código
de negócio (Hexagonal Architecture / Ports & Adapters).

Exemplo: trocar de Stripe para MercadoPago requer apenas um novo adapter
que implemente IPaymentGateway, sem alterar nenhum service ou route.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IIntegrationProvider(ABC):
    """
    Interface base para todos os provedores de integração.
    """
    @abstractmethod
    def __init__(self, credentials: Dict[str, Any]):
        pass

    @abstractmethod
    def ping(self) -> bool:
        """Verifica se o provider está acessível com as credenciais atuais."""
        pass


class IMessagingProvider(IIntegrationProvider):
    """Port para disparo de mensagens (WhatsApp, Telegram, SMS, etc).

    Inclui métodos sync para uso em workers assíncronos (ex: Celery prefork)
    e métodos async para uso em frameworks web (ex: FastAPI).
    """

    @abstractmethod
    async def send_template(self, target: str, template_name: str, variables: Dict[str, str]) -> Dict[str, Any]:
        """Envia mensagem baseada em template."""
        pass

    @abstractmethod
    async def send_text(self, target: str, text: str) -> Dict[str, Any]:
        """Envio assíncrono de texto."""
        pass

    @abstractmethod
    def send_text_sync(self, target: str, text: str) -> Dict[str, Any]:
        """Envio síncrono de texto (para workers síncronos como Celery)."""
        pass

    @abstractmethod
    async def send_buttons(self, target: str, title: str, description: str, buttons: List[dict]) -> Dict[str, Any]:
        """Envia mensagem interativa com botões."""
        pass


class IEmailProvider(IIntegrationProvider):
    """Port para disparo de Email."""

    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        pass


class IPaymentGateway(IIntegrationProvider):
    """Port para Gateways de Pagamento (PIX/Cartão/Boleto)."""

    @abstractmethod
    async def create_charge(
        self,
        amount: float,
        external_reference: str,
        payer_name: str,
        payer_document: str,
    ) -> Dict[str, Any]:
        pass


class IShippingProvider(IIntegrationProvider):
    """Port para cotação e rastreio de Frete."""

    @abstractmethod
    async def calculate_shipping(
        self,
        origin_zip: str,
        destination_zip: str,
        weight_kg: float,
        dimensions_cm: tuple[float, float, float],
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def track_shipment(self, tracking_code: str) -> Dict[str, Any]:
        """Consulta o rastreamento de uma encomenda."""
        pass
