"""
Example: Governance Layer — Constitution + Mediator.

Demonstrates:
- Invariant enforcement with @invariant_guard decorator
- Imperative invariant checking with Constitution.enforce()
- Cross-domain conflict mediation with DomainMediator
"""
from governance.constitution import (
    Constitution,
    InvariantRule,
    InvariantViolation,
    invariant_guard,
)
from governance.mediator import (
    DomainMediator,
    EscalationReason,
    MediatorDecision,
)


def main():
    print("=" * 60)
    print("Governance Layer Demo")
    print("=" * 60)

    # ── 1. Constitution — Invariant Enforcement ──────────────
    print("\n📜 Constitution — Invariant Enforcement")
    print("-" * 40)

    # Test 1: Valid context (should pass)
    valid_context = {"user_id": 42, "current_user": type("User", (), {"id": 42, "is_superuser": False})()}
    is_valid, msg = Constitution.check(InvariantRule.REQUIRE_AUTHENTICATION, valid_context)
    print(f"   ✅ Auth check (valid user): is_valid={is_valid}")

    # Test 2: Missing auth (should fail)
    empty_context = {}
    is_valid, msg = Constitution.check(InvariantRule.REQUIRE_AUTHENTICATION, empty_context)
    print(f"   ❌ Auth check (no user): is_valid={is_valid}, detail='{msg}'")

    # Test 3: Financial limits (negative amount)
    financial_context = {"amount": -100}
    is_valid, msg = Constitution.check(InvariantRule.ENFORCE_FINANCIAL_LIMITS, financial_context)
    print(f"   ❌ Financial check (negative): is_valid={is_valid}, detail='{msg}'")

    # Test 4: Domain boundary violation
    cross_domain_ctx = {"source_domain": "ordering", "target_domain": "billing", "via_event": False}
    is_valid, msg = Constitution.check(InvariantRule.ENFORCE_DOMAIN_BOUNDARIES, cross_domain_ctx)
    print(f"   ❌ Domain boundary check: is_valid={is_valid}")
    print(f"      detail='{msg}'")

    # Test 5: Check all invariants at once
    print("\n   Check ALL invariants against empty context:")
    violations = Constitution.check_all({})
    for rule, detail in violations:
        print(f"      ⚠️  {rule.value}: {detail}")

    # Test 6: Enforcement (raises exception)
    print("\n   Enforcement (raises InvariantViolation):")
    try:
        Constitution.enforce(InvariantRule.REQUIRE_AUTHENTICATION, {}, domain="ordering")
    except InvariantViolation as e:
        print(f"      🚨 Caught: {e}")

    # ── 2. Mediator — Cross-Domain Conflict Resolution ───────
    print(f"\n\n🤝 Mediator — Cross-Domain Conflict Resolution")
    print("-" * 40)

    # Configure mediator with domain policies
    mediator = DomainMediator(
        domain_policies={
            "ordering": {"allowed_operations": ["create_order", "cancel_order", "update_order"]},
            "billing": {"allowed_operations": ["charge", "refund", "invoice"]},
            "identity": {"allowed_operations": ["auth", "rbac", "sessions", "users"]},
        }
    )

    # Test 1: Ambiguity resolution
    verdict = mediator.mediate(
        reason=EscalationReason.AMBIGUITY,
        source_domain="ordering",
        context={"operation": "charge"},
    )
    print(f"   Ambiguity: '{verdict.justification}'")
    print(f"   → Decision: {verdict.decision.value}, Delegated to: {verdict.delegated_domain}")

    # Test 2: Conflict resolution (hierarchy-based)
    verdict = mediator.mediate(
        reason=EscalationReason.CONFLICT,
        source_domain="ordering",
        target_domain="billing",
        conflicting_rules=[
            {"name": "platform_rule", "level": "PLATFORM", "action": "allow"},
            {"name": "module_rule", "level": "MODULE", "action": "deny"},
        ],
        context={},
    )
    print(f"\n   Conflict: '{verdict.justification}'")
    print(f"   → Decision: {verdict.decision.value}, Winner: {verdict.exception_rule}")

    # Test 3: Cross-domain direct access (should deny)
    verdict = mediator.mediate(
        reason=EscalationReason.CROSS_DOMAIN,
        source_domain="ordering",
        target_domain="billing",
        context={},
    )
    print(f"\n   Cross-domain: '{verdict.justification}'")
    print(f"   → Decision: {verdict.decision.value}")

    # Test 4: Missing context
    verdict = mediator.mediate(
        reason=EscalationReason.MISSING_CONTEXT,
        source_domain="ordering",
        context={"missing_fields": ["customer_id", "shipping_address"]},
    )
    print(f"\n   Missing context: '{verdict.justification}'")
    print(f"   → Decision: {verdict.decision.value}")

    print(f"\n{'='*60}")
    print("Done!")


if __name__ == "__main__":
    main()
