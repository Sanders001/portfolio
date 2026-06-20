"""
Mediator — Cross-Domain Conflict Resolution.

O Mediator é invocado apenas em situações excepcionais:
- Ambiguidade: múltiplos domínios podem resolver o mesmo evento
- Conflito: regras de domínios diferentes se contradizem
- Falta de contexto: informações insuficientes para decisão
- Exceção: violação de invariante que requer mediação
- Cross-domain: acesso direto entre domínios sem evento

O Mediator NÃO governa — ele media. Toda decisão é registrada
para auditoria.
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class EscalationReason(str, Enum):
    """Motivos para escalonamento ao Mediator."""
    AMBIGUITY = "AMBIGUITY"               # Múltiplos domínios respondem
    CONFLICT = "CONFLICT"                 # Regras conflitantes entre domínios
    MISSING_CONTEXT = "MISSING_CONTEXT"   # Informações insuficientes
    INVARIANT = "INVARIANT"               # Violação de invariante detectada
    CROSS_DOMAIN = "CROSS_DOMAIN"         # Operação cross-domain sem evento


class MediatorDecision(str, Enum):
    """Decisões possíveis do Mediator."""
    ALLOW = "ALLOW"             # Permitir a ação
    DENY = "DENY"               # Bloquear a ação
    DELEGATE = "DELEGATE"       # Delegar a um domínio específico
    ESCALATE = "ESCALATE"       # Escalonar para decisão humana


@dataclass
class MediatorVerdict:
    """Resultado de uma mediação."""
    decision: MediatorDecision
    reason: EscalationReason
    justification: str
    delegated_domain: Optional[str] = None
    exception_rule: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verdict_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class DomainMediator:
    """
    Mediador interdomínio da plataforma.

    Princípios:
    1. Não governa, media — só é invocado em exceções
    2. Consulta políticas existentes antes de decidir
    3. Toda decisão é registrada para auditoria
    4. Quando não consegue resolver, escalona

    Args:
        domain_policies: Dict mapeando domínio → dict de configuração.
            Ex: {"ordering": {"allowed_operations": ["create", "cancel"]}}
        verdict_recorder: Callback opcional para persistir verdicts.
            Recebe (verdict, source_domain, target_domain, context).

    Usage:
        mediator = DomainMediator(
            domain_policies={
                "ordering": {"allowed_operations": ["create", "cancel", "update"]},
                "billing": {"allowed_operations": ["charge", "refund", "invoice"]},
                "identity": {"allowed_operations": ["auth", "rbac", "sessions"]},
            }
        )
        verdict = mediator.mediate(
            reason=EscalationReason.CONFLICT,
            source_domain="ordering",
            target_domain="billing",
            context={"event": "order.paid"},
        )
    """

    def __init__(
        self,
        domain_policies: Optional[dict[str, dict]] = None,
        verdict_recorder: Optional[Callable] = None,
    ) -> None:
        self._policies: dict[str, dict] = domain_policies or {}
        self._verdict_recorder = verdict_recorder

    def mediate(
        self,
        reason: EscalationReason,
        source_domain: str,
        context: dict[str, Any],
        target_domain: Optional[str] = None,
        conflicting_rules: Optional[list[dict]] = None,
    ) -> MediatorVerdict:
        """
        Ponto de entrada para mediação.

        Args:
            reason: Motivo do escalonamento
            source_domain: Domínio que originou a ação
            context: Contexto da operação
            target_domain: Domínio alvo (se cross-domain)
            conflicting_rules: Regras em conflito (se CONFLICT)

        Returns:
            MediatorVerdict com a decisão e justificativa
        """
        logger.info(
            f"[mediator] Mediation requested: reason={reason.value} "
            f"source={source_domain} target={target_domain}"
        )

        # Despacho por tipo de escalonamento
        if reason == EscalationReason.AMBIGUITY:
            verdict = self._resolve_ambiguity(source_domain, context)
        elif reason == EscalationReason.CONFLICT:
            verdict = self._resolve_conflict(
                source_domain, target_domain, conflicting_rules or [], context
            )
        elif reason == EscalationReason.MISSING_CONTEXT:
            verdict = self._resolve_missing_context(source_domain, context)
        elif reason == EscalationReason.INVARIANT:
            verdict = self._resolve_invariant_violation(source_domain, context)
        elif reason == EscalationReason.CROSS_DOMAIN:
            verdict = self._resolve_cross_domain(
                source_domain, target_domain or "unknown", context
            )
        else:
            verdict = MediatorVerdict(
                decision=MediatorDecision.ESCALATE,
                reason=reason,
                justification="Unrecognized escalation reason — escalating",
            )

        # Registra no log de exceções
        self._record_verdict(verdict, source_domain, target_domain, context)

        return verdict

    # ── Resolvedores ──────────────────────────────────────────

    def _resolve_ambiguity(
        self, source_domain: str, context: dict
    ) -> MediatorVerdict:
        """
        Quando múltiplos domínios podem responder a um evento,
        o Mediator decide qual tem jurisdição.
        """
        operation = context.get("operation", "")
        best_domain = self._find_domain_for_operation(operation)

        if best_domain:
            return MediatorVerdict(
                decision=MediatorDecision.DELEGATE,
                reason=EscalationReason.AMBIGUITY,
                justification=(
                    f"Operation '{operation}' resolved: delegated to domain "
                    f"'{best_domain}' by jurisdiction"
                ),
                delegated_domain=best_domain,
            )

        return MediatorVerdict(
            decision=MediatorDecision.ESCALATE,
            reason=EscalationReason.AMBIGUITY,
            justification=(
                f"Operation '{operation}' is ambiguous — no domain has "
                f"clear jurisdiction. Escalating for human decision."
            ),
        )

    def _resolve_conflict(
        self,
        source_domain: str,
        target_domain: Optional[str],
        conflicting_rules: list[dict],
        context: dict,
    ) -> MediatorVerdict:
        """
        Quando regras de domínios diferentes se contradizem,
        a regra de nível mais alto prevalece (PLATFORM > DOMAIN > MODULE).
        """
        LEVEL_PRIORITY = {"PLATFORM": 0, "DOMAIN": 1, "MODULE": 2}

        if conflicting_rules:
            sorted_rules = sorted(
                conflicting_rules,
                key=lambda r: LEVEL_PRIORITY.get(r.get("level", "MODULE"), 2),
            )
            winner = sorted_rules[0]
            return MediatorVerdict(
                decision=MediatorDecision.ALLOW,
                reason=EscalationReason.CONFLICT,
                justification=(
                    f"Conflict resolved by hierarchical precedence: "
                    f"rule '{winner.get('name')}' (level {winner.get('level')}) "
                    f"prevails over lower-level rules"
                ),
                exception_rule=winner.get("name"),
                metadata={"winning_rule": winner, "all_rules": conflicting_rules},
            )

        return MediatorVerdict(
            decision=MediatorDecision.ESCALATE,
            reason=EscalationReason.CONFLICT,
            justification="Conflict with no rules to compare — escalating",
        )

    def _resolve_missing_context(
        self, source_domain: str, context: dict
    ) -> MediatorVerdict:
        """Contexto insuficiente — nega a operação até que informações sejam fornecidas."""
        missing = context.get("missing_fields", [])
        return MediatorVerdict(
            decision=MediatorDecision.DENY,
            reason=EscalationReason.MISSING_CONTEXT,
            justification=(
                f"Operation from domain '{source_domain}' denied: "
                f"insufficient context. Missing fields: {missing}"
            ),
            metadata={"missing_fields": missing},
        )

    def _resolve_invariant_violation(
        self, source_domain: str, context: dict
    ) -> MediatorVerdict:
        """Violação de invariante — sempre nega e registra."""
        violated_rule = context.get("violated_rule", "unknown")
        return MediatorVerdict(
            decision=MediatorDecision.DENY,
            reason=EscalationReason.INVARIANT,
            justification=(
                f"Invariant violation by domain '{source_domain}': "
                f"rule '{violated_rule}' was violated. Operation blocked."
            ),
            exception_rule=violated_rule,
        )

    def _resolve_cross_domain(
        self,
        source_domain: str,
        target_domain: str,
        context: dict,
    ) -> MediatorVerdict:
        """
        Operação cross-domain sem evento intermediário.
        Nega e sugere uso do Event Bus.
        """
        return MediatorVerdict(
            decision=MediatorDecision.DENY,
            reason=EscalationReason.CROSS_DOMAIN,
            justification=(
                f"Domain '{source_domain}' attempted direct access to domain "
                f"'{target_domain}'. Inter-domain communication must use the "
                f"Event Bus. Operation blocked."
            ),
        )

    # ── Helpers ────────────────────────────────────────────────

    def _find_domain_for_operation(self, operation: str) -> Optional[str]:
        """Resolve qual domínio tem jurisdição sobre uma operação."""
        for domain, policy in self._policies.items():
            if operation in policy.get("allowed_operations", []):
                return domain
        return None

    def _record_verdict(
        self,
        verdict: MediatorVerdict,
        source_domain: str,
        target_domain: Optional[str],
        context: dict,
    ) -> None:
        """Registra a decisão para auditoria."""
        logger.info(
            f"[mediator] Verdict recorded: id={verdict.verdict_id} "
            f"decision={verdict.decision.value}"
        )

        if self._verdict_recorder:
            try:
                self._verdict_recorder(verdict, source_domain, target_domain, context)
            except Exception as e:
                # Não bloqueia a operação se o registro falhar
                logger.warning(f"[mediator] Failed to record verdict: {e}")
