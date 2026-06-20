"""
Constitution — Regras Pétreas (Invariant Enforcement).

Define as invariantes absolutas que nenhum domínio, módulo ou agente pode violar.

Uso:
    @invariant_guard(InvariantRule.REQUIRE_AUTHENTICATION)
    async def create_order(...):
        ...

    # Ou verificação imperativa:
    Constitution.enforce(InvariantRule.REQUIRE_AUTHENTICATION, context)
"""
import logging
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ── Regras Pétreas (Invariantes) ─────────────────────────────────
class InvariantRule(str, Enum):
    """
    Artigos constitucionais — regras invioláveis da plataforma.
    Cada regra mapeia para uma validação específica.
    """

    REQUIRE_AUTHENTICATION = "INV_1__REQUIRE_AUTHENTICATION"
    """Nenhuma operação transacional pode ser processada sem usuário autenticado."""

    REQUIRE_AUTHORIZATION = "INV_2__REQUIRE_AUTHORIZATION"
    """Nenhuma ação crítica pode ser executada sem permissão explícita."""

    ENFORCE_FINANCIAL_LIMITS = "INV_3__ENFORCE_FINANCIAL_LIMITS"
    """Nenhuma operação financeira pode violar políticas de margem, limites ou compliance."""

    ENFORCE_DOMAIN_BOUNDARIES = "INV_4__ENFORCE_DOMAIN_BOUNDARIES"
    """Nenhum domínio pode executar ações fora de sua jurisdição."""


# ── Exceção Constitucional ────────────────────────────────────
class InvariantViolation(Exception):
    """
    Exceção levantada quando uma regra pétrea é violada.
    """

    def __init__(
        self,
        rule: InvariantRule,
        domain: str = "unknown",
        detail: str = "",
        context: Optional[dict] = None,
    ):
        self.rule = rule
        self.domain = domain
        self.detail = detail
        self.context = context or {}
        super().__init__(
            f"Invariant Violation [{rule.value}]: {detail}"
        )


# ── Validadores por Regra ─────────────────────────────────────
class _InvariantValidators:
    """
    Validadores concretos para cada regra pétrea.
    Cada método retorna (is_valid, detail_message).
    """

    @staticmethod
    def validate_auth_present(context: dict) -> tuple[bool, str]:
        """INV_1: Verifica se há usuário autenticado no contexto."""
        user = context.get("current_user") or context.get("user_id")
        if not user:
            return False, "Operation requires authenticated user"
        return True, ""

    @staticmethod
    def validate_permission(context: dict) -> tuple[bool, str]:
        """INV_2: Verifica se há permissão explícita para a ação."""
        user = context.get("current_user")
        if user and hasattr(user, "is_superuser") and not user.is_superuser:
            required = context.get("required_permission")
            if required:
                return False, f"Permission '{required}' is missing"
        return True, ""

    @staticmethod
    def validate_financial_limits(context: dict) -> tuple[bool, str]:
        """INV_3: Verifica políticas financeiras básicas."""
        amount = context.get("amount", 0)
        if amount is not None and amount < 0:
            return False, "Negative financial amounts are not allowed"
        return True, ""

    @staticmethod
    def validate_domain_boundaries(context: dict) -> tuple[bool, str]:
        """INV_4: Verifica se o domínio está agindo dentro de seu escopo."""
        source_domain = context.get("source_domain")
        target_domain = context.get("target_domain")
        if source_domain and target_domain and source_domain != target_domain:
            # Cross-domain direto sem evento — violação
            if not context.get("via_event", False):
                return False, (
                    f"Domain '{source_domain}' attempted direct action on "
                    f"domain '{target_domain}' without an inter-domain event"
                )
        return True, ""


# ── Mapeamento Regra → Validador ──────────────────────────────
_RULE_VALIDATORS: dict[InvariantRule, Callable] = {
    InvariantRule.REQUIRE_AUTHENTICATION: _InvariantValidators.validate_auth_present,
    InvariantRule.REQUIRE_AUTHORIZATION: _InvariantValidators.validate_permission,
    InvariantRule.ENFORCE_FINANCIAL_LIMITS: _InvariantValidators.validate_financial_limits,
    InvariantRule.ENFORCE_DOMAIN_BOUNDARIES: _InvariantValidators.validate_domain_boundaries,
}


# ── Enforcement Central ───────────────────────────────────────
class Constitution:
    """
    Ponto central de enforcement das regras pétreas.

    Uso imperativo:
        Constitution.enforce(InvariantRule.REQUIRE_AUTHENTICATION, {"user_id": 1})

    Uso como decorator:
        @invariant_guard(InvariantRule.REQUIRE_AUTHENTICATION)
        async def my_endpoint(request, current_user):
            ...
    """

    @staticmethod
    def enforce(
        rule: InvariantRule,
        context: dict,
        domain: str = "unknown",
    ) -> None:
        """
        Valida uma regra pétrea. Levanta InvariantViolation se violada.
        """
        validator = _RULE_VALIDATORS.get(rule)
        if not validator:
            logger.warning(f"[constitution] Rule '{rule.value}' has no registered validator")
            return

        is_valid, detail = validator(context)
        if not is_valid:
            logger.error(
                f"[constitution] VIOLATION: {rule.value} | domain={domain} | {detail}"
            )
            raise InvariantViolation(
                rule=rule,
                domain=domain,
                detail=detail,
                context=context,
            )

    @staticmethod
    def check(
        rule: InvariantRule,
        context: dict,
    ) -> tuple[bool, str]:
        """
        Verifica uma regra pétrea sem levantar exceção.
        Retorna (is_valid, detail_message).
        """
        validator = _RULE_VALIDATORS.get(rule)
        if not validator:
            return True, ""
        return validator(context)

    @staticmethod
    def check_all(context: dict) -> list[tuple[InvariantRule, str]]:
        """
        Verifica todas as regras pétreas contra o contexto.
        Retorna lista de (regra, detalhe) para as violadas.
        """
        violations = []
        for rule, validator in _RULE_VALIDATORS.items():
            is_valid, detail = validator(context)
            if not is_valid:
                violations.append((rule, detail))
        return violations


# ── Decorator ─────────────────────────────────────────────────
def invariant_guard(
    rule: InvariantRule,
    domain: str = "unknown",
    context_extractor: Optional[Callable] = None,
):
    """
    Decorator que valida uma regra pétrea antes da execução de uma função.

    Para rotas FastAPI, extrai automaticamente `current_user` dos kwargs.
    Para funções genéricas, aceita um `context_extractor` customizado.

    Exemplo:
        @invariant_guard(InvariantRule.REQUIRE_AUTHENTICATION, domain="ordering")
        async def create_order(request, current_user=Depends(...)):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            ctx = _extract_context(kwargs, context_extractor)
            Constitution.enforce(rule, ctx, domain=domain)
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            ctx = _extract_context(kwargs, context_extractor)
            Constitution.enforce(rule, ctx, domain=domain)
            return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _extract_context(
    kwargs: dict,
    extractor: Optional[Callable] = None,
) -> dict:
    """Extrai contexto dos kwargs da função para validação constitucional."""
    if extractor:
        return extractor(kwargs)

    # Default: extrai current_user e request dos kwargs
    context: dict[str, Any] = {}
    if "current_user" in kwargs:
        context["current_user"] = kwargs["current_user"]
        context["user_id"] = getattr(kwargs["current_user"], "id", None)
    if "request" in kwargs:
        context["request"] = kwargs["request"]
    # Merge com kwargs adicionais úteis
    for key in ("amount", "source_domain", "target_domain", "via_event"):
        if key in kwargs:
            context[key] = kwargs[key]

    return context
