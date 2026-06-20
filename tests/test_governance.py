"""
Tests for the Governance Layer.

Covers: Constitution (invariant enforcement), Mediator (cross-domain resolution).
"""
import pytest
from governance.constitution import (
    Constitution,
    InvariantRule,
    InvariantViolation,
)
from governance.mediator import (
    DomainMediator,
    EscalationReason,
    MediatorDecision,
)


# ── Constitution Tests ────────────────────────────────────────

class TestConstitution:
    def test_auth_check_passes_with_user(self):
        ctx = {"user_id": 1}
        is_valid, _ = Constitution.check(InvariantRule.REQUIRE_AUTHENTICATION, ctx)
        assert is_valid is True

    def test_auth_check_fails_without_user(self):
        is_valid, detail = Constitution.check(InvariantRule.REQUIRE_AUTHENTICATION, {})
        assert is_valid is False
        assert "authenticated" in detail.lower()

    def test_financial_check_rejects_negative(self):
        ctx = {"amount": -50}
        is_valid, _ = Constitution.check(InvariantRule.ENFORCE_FINANCIAL_LIMITS, ctx)
        assert is_valid is False

    def test_financial_check_accepts_positive(self):
        ctx = {"amount": 100}
        is_valid, _ = Constitution.check(InvariantRule.ENFORCE_FINANCIAL_LIMITS, ctx)
        assert is_valid is True

    def test_domain_boundary_blocks_direct_cross_domain(self):
        ctx = {"source_domain": "ordering", "target_domain": "billing", "via_event": False}
        is_valid, _ = Constitution.check(InvariantRule.ENFORCE_DOMAIN_BOUNDARIES, ctx)
        assert is_valid is False

    def test_domain_boundary_allows_via_event(self):
        ctx = {"source_domain": "ordering", "target_domain": "billing", "via_event": True}
        is_valid, _ = Constitution.check(InvariantRule.ENFORCE_DOMAIN_BOUNDARIES, ctx)
        assert is_valid is True

    def test_enforce_raises_on_violation(self):
        with pytest.raises(InvariantViolation) as exc_info:
            Constitution.enforce(InvariantRule.REQUIRE_AUTHENTICATION, {}, domain="test")
        assert exc_info.value.domain == "test"
        assert exc_info.value.rule == InvariantRule.REQUIRE_AUTHENTICATION

    def test_check_all_returns_multiple_violations(self):
        violations = Constitution.check_all({})
        # At minimum, auth should fail
        rule_names = [v[0] for v in violations]
        assert InvariantRule.REQUIRE_AUTHENTICATION in rule_names


# ── Mediator Tests ────────────────────────────────────────────

class TestMediator:
    @pytest.fixture
    def mediator(self):
        return DomainMediator(
            domain_policies={
                "ordering": {"allowed_operations": ["create", "cancel"]},
                "billing": {"allowed_operations": ["charge", "refund"]},
            }
        )

    def test_ambiguity_delegates_to_correct_domain(self, mediator):
        verdict = mediator.mediate(
            reason=EscalationReason.AMBIGUITY,
            source_domain="unknown",
            context={"operation": "charge"},
        )
        assert verdict.decision == MediatorDecision.DELEGATE
        assert verdict.delegated_domain == "billing"

    def test_ambiguity_escalates_when_no_match(self, mediator):
        verdict = mediator.mediate(
            reason=EscalationReason.AMBIGUITY,
            source_domain="unknown",
            context={"operation": "fly_to_moon"},
        )
        assert verdict.decision == MediatorDecision.ESCALATE

    def test_conflict_resolved_by_hierarchy(self, mediator):
        verdict = mediator.mediate(
            reason=EscalationReason.CONFLICT,
            source_domain="ordering",
            target_domain="billing",
            conflicting_rules=[
                {"name": "low_rule", "level": "MODULE"},
                {"name": "high_rule", "level": "PLATFORM"},
            ],
            context={},
        )
        assert verdict.decision == MediatorDecision.ALLOW
        assert verdict.exception_rule == "high_rule"

    def test_cross_domain_denied(self, mediator):
        verdict = mediator.mediate(
            reason=EscalationReason.CROSS_DOMAIN,
            source_domain="ordering",
            target_domain="billing",
            context={},
        )
        assert verdict.decision == MediatorDecision.DENY

    def test_missing_context_denied(self, mediator):
        verdict = mediator.mediate(
            reason=EscalationReason.MISSING_CONTEXT,
            source_domain="ordering",
            context={"missing_fields": ["customer_id"]},
        )
        assert verdict.decision == MediatorDecision.DENY

    def test_verdict_has_unique_id(self, mediator):
        v1 = mediator.mediate(EscalationReason.CROSS_DOMAIN, "a", {})
        v2 = mediator.mediate(EscalationReason.CROSS_DOMAIN, "b", {})
        assert v1.verdict_id != v2.verdict_id

    def test_verdict_recorder_is_called(self):
        recorded = []

        def recorder(verdict, source, target, context):
            recorded.append(verdict)

        mediator = DomainMediator(verdict_recorder=recorder)
        mediator.mediate(EscalationReason.CROSS_DOMAIN, "a", {}, "b")

        assert len(recorded) == 1
        assert recorded[0].decision == MediatorDecision.DENY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
