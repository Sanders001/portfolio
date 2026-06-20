"""
Example: Integration Layer — Plugin System with Auto-Discovery.

Demonstrates:
- Defining integration interfaces (Ports)
- Registering adapters with @integration_provider decorator
- Resolving the correct provider at runtime per tenant
"""
from integrations.interfaces import IPaymentGateway, IMessagingProvider
from integrations.registry import integration_provider, ProviderRegistry
from integrations.resolver import ProviderResolver
from typing import Any, Dict, List


# ═══════════════════════════════════════════════════════════════
# 1. ADAPTERS — Implementações concretas auto-registradas
# ═══════════════════════════════════════════════════════════════

@integration_provider("payment.stripe")
class StripeAdapter(IPaymentGateway):
    """Adapter para Stripe."""

    def __init__(self, credentials: Dict[str, Any]):
        self.api_key = credentials.get("api_key", "")
        self.name = "Stripe"

    def ping(self) -> bool:
        return bool(self.api_key)

    async def create_charge(self, amount, external_reference, payer_name, payer_document):
        return {
            "provider": self.name,
            "charge_id": f"ch_{external_reference}",
            "amount": amount,
            "status": "pending",
        }


@integration_provider("payment.mercadopago")
class MercadoPagoAdapter(IPaymentGateway):
    """Adapter para MercadoPago."""

    def __init__(self, credentials: Dict[str, Any]):
        self.access_token = credentials.get("access_token", "")
        self.name = "MercadoPago"

    def ping(self) -> bool:
        return bool(self.access_token)

    async def create_charge(self, amount, external_reference, payer_name, payer_document):
        return {
            "provider": self.name,
            "charge_id": f"mp_{external_reference}",
            "amount": amount,
            "status": "pending",
        }


@integration_provider("messaging.console")
class ConsoleMessagingAdapter(IMessagingProvider):
    """Adapter de messaging que imprime no console (para demo)."""

    def __init__(self, credentials: Dict[str, Any]):
        self.name = "Console"

    def ping(self) -> bool:
        return True

    async def send_template(self, target, template_name, variables):
        print(f"  [Console] Template '{template_name}' → {target} | vars={variables}")
        return {"status": "sent"}

    async def send_text(self, target, text):
        print(f"  [Console] Text → {target}: {text}")
        return {"status": "sent"}

    def send_text_sync(self, target, text):
        print(f"  [Console/Sync] Text → {target}: {text}")
        return {"status": "sent"}

    async def send_buttons(self, target, title, description, buttons):
        print(f"  [Console] Buttons → {target}: {title}")
        return {"status": "sent"}


# ═══════════════════════════════════════════════════════════════
# 2. DEMO — Resolvendo providers em runtime
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("Integration Layer Demo")
    print("=" * 60)

    # 1. Listar providers registrados automaticamente
    all_providers = ProviderRegistry.get_all()
    print(f"\n📦 Registered providers ({len(all_providers)}):")
    for key, cls in all_providers.items():
        print(f"   {key} → {cls.__name__}")

    # 2. Configurar resolução por tenant (simulado)
    tenant_settings = {
        "tenant_acme": {"payment": "payment.stripe"},
        "tenant_beta": {"payment": "payment.mercadopago"},
    }
    tenant_credentials = {
        "tenant_acme": {"payment": {"api_key": "sk_test_acme_123"}},
        "tenant_beta": {"payment": {"access_token": "mp_token_beta_456"}},
    }

    def load_settings(tenant_id: str, provider_type: str):
        return tenant_settings.get(tenant_id, {}).get(provider_type)

    def load_credentials(tenant_id: str, provider_type: str):
        return tenant_credentials.get(tenant_id, {}).get(provider_type, {})

    resolver = ProviderResolver(
        settings_loader=load_settings,
        credentials_loader=load_credentials,
        defaults={"payment": "payment.stripe", "messaging": "messaging.console"},
    )

    # 3. Resolver providers para diferentes tenants
    print("\n🔀 Resolving providers per tenant:")

    for tenant_id in ["tenant_acme", "tenant_beta", "tenant_unknown"]:
        provider = resolver.resolve(tenant_id, "payment")
        print(f"   {tenant_id} → {provider.name} (ping={provider.ping()})")

    # 4. Resolver messaging com fallback
    print("\n💬 Messaging resolver (fallback to default):")
    messaging = resolver.resolve("any_tenant", "messaging")
    messaging.send_text_sync("user@example.com", "Hello from the integration layer!")

    # Limpar para não afetar outros testes
    ProviderRegistry.clear()

    print(f"\n{'='*60}")
    print("Done!")


if __name__ == "__main__":
    main()
