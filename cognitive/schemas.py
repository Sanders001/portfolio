"""
Cognitive Engine — Schemas Genéricos.

Contratos de entrada/saída do engine cognitivo, independentes de domínio.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

# ─── Enums ────────────────────────────────────────────────────


class CognitiveSource(str, Enum):
    """Origem da resolução cognitiva."""
    intercept = "intercept"       # Resolvido por InterceptHandler (determinístico)
    reuse = "reuse"               # Resolvido por cache semântico (Memória)
    local_intent = "local_intent" # Resolvido por short-circuit via IntentMatcher
    llm = "llm"                   # Resolvido por LLM fallback
    fallback = "fallback"         # Nenhum estágio conseguiu resolver


# ─── Classification Result ────────────────────────────────────


@dataclass
class ClassificationResult:
    """
    Resultado estruturado de uma classificação (FAISS ou LLM).

    Unifica diferentes tipos de classificação em um contrato comum
    consumido pelo Pipeline e pelo DomainStrategy.
    """
    intent: str
    confidence: float
    intents: list[str] = field(default_factory=list)
    entities: dict[str, Any] = field(default_factory=dict)
    raw_response: str = ""
    model_used: str = ""
    latency_ms: int = 0


# ─── Pipeline I/O ─────────────────────────────────────────────


@dataclass
class CognitiveInput:
    """
    Entrada genérica para o pipeline cognitivo.

    Campos essenciais que qualquer domínio precisa fornecer.
    O campo `domain_data` transporta dados específicos do domínio
    sem que o engine precise conhecê-los.
    """
    text: str
    session_id: str                          # Identificador da sessão
    state: Optional[Any] = None              # Estado cognitivo (tipado em runtime)
    context: dict[str, Any] = field(default_factory=dict)
    message_id: Optional[str] = None
    domain_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class CognitiveResult:
    """
    Resultado genérico do pipeline cognitivo.

    Transporta a resposta final + metadados de observabilidade.
    """
    intent: Optional[str] = None
    intents: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source: CognitiveSource = CognitiveSource.fallback
    response_text: Optional[str] = None
    entities: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0

    # ── Observabilidade (Pilar 4 — Revisão) ───────────────────
    latency_intent_ms: Optional[int] = None
    latency_reuse_ms: Optional[int] = None
    latency_llm_ms: Optional[int] = None
    local_intent: Optional[str] = None
    fallback_reason: Optional[str] = None
    skipped_to_llm: bool = False
