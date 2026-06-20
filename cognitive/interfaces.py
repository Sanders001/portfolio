"""
Cognitive Engine — Contratos Abstratos (Interfaces).

Define os contratos que cada domínio especialista deve implementar
para se conectar à infraestrutura cognitiva.

Baseado na Teoria dos 4 Pilares Cognitivos:
  - O engine fornece: Interpretação, Memória, Lógica Processual, Revisão
  - O domínio fornece: Strategy, Orchestrator, Interceptors, Seeds
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from .schemas import ClassificationResult, CognitiveInput, CognitiveResult

# ── Pilar 2 (Lógica Processual) — Contratos de Domínio ────────


class DomainStrategy(ABC):
    """
    Contrato que cada domínio especialista deve implementar.

    Responsável por transformar uma classificação (intent + entities)
    em resposta textual final, aplicando regras de negócio do domínio.
    """

    @abstractmethod
    def resolve(
        self,
        result: ClassificationResult,
        state: Optional[Any] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Gera resposta textual a partir da classificação.

        Args:
            result: Classificação com intent, entities e confidence
            state: Estado cognitivo da sessão
            context: Contexto enriquecido (dados do usuário, etc.)

        Returns:
            Texto de resposta pronto para envio
        """
        ...

    @abstractmethod
    def get_required_entities(self, intent: str) -> dict:
        """
        Retorna schema de entidades requeridas para um intent específico.

        Returns:
            Dict com chaves 'required' (list[str]), 'prompt_text' (str), etc.
            Retorna dict vazio se o intent não requer entidades adicionais.
        """
        ...

    @abstractmethod
    def get_seed_path(self) -> Path:
        """
        Retorna o caminho para o arquivo seed de intents do domínio.

        Cada domínio possui seu próprio conjunto de intents.
        """
        ...


class DomainOrchestrator(ABC):
    """
    Orquestrador narrativo específico do domínio.

    Pós-processa a resposta gerada pelo DomainStrategy para garantir
    continuidade, progressão e coerência narrativa.
    """

    @abstractmethod
    def build_response(
        self,
        base_text: str,
        state: Optional[Any],
        intent: str,
    ) -> str:
        """
        Constrói a resposta orquestrada.

        Args:
            base_text: Resposta base gerada pelo DomainStrategy
            state: Estado cognitivo da sessão
            intent: Intent classificado

        Returns:
            Resposta com personalizações narrativas aplicadas
        """
        ...


class InterceptHandler(ABC):
    """
    Handler para interceptação determinística de mensagens.

    Interceptadores resolvem mensagens sem acionar FAISS ou LLM,
    usado para fluxos determinísticos (menus, formulários, wizards).

    O Pipeline itera sobre a lista de interceptadores registrados
    e o primeiro que retorna `can_handle=True` resolve a mensagem.
    """

    @abstractmethod
    def can_handle(self, inp: CognitiveInput) -> bool:
        """
        Verifica se este handler deve interceptar o input.

        Args:
            inp: Entrada cognitiva com texto, estado e contexto

        Returns:
            True se este handler deve processar o input
        """
        ...

    @abstractmethod
    def handle(self, inp: CognitiveInput) -> CognitiveResult:
        """
        Processa o input de forma determinística.

        Args:
            inp: Entrada cognitiva

        Returns:
            CognitiveResult com resposta determinística
        """
        ...


# ── Pilar 1 (Interpretação) — Contratos de Provedor ───────────


class LLMProviderInterface(ABC):
    """
    Interface abstrata para provedores de LLM.

    O LLM é invocado APENAS como fallback — nunca como core.
    Retorna uma classificação estruturada, nunca texto livre diretamente.
    """

    @abstractmethod
    def classify(
        self,
        text: str,
        history: list[str],
        state_context: dict[str, Any],
        user_context: dict[str, Any] | None = None,
    ) -> ClassificationResult:
        """
        Classifica o texto do usuário e retorna intent + entities.

        Args:
            text: Mensagem normalizada do usuário
            history: Últimas N mensagens da conversa
            state_context: Estado conversacional atual
            user_context: Dados reais do usuário

        Returns:
            ClassificationResult com intent, entities e confidence
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o provedor está configurado e disponível."""
        ...


# ── Pilar 4 (Revisão) — Contratos de Observabilidade ──────────


class MetricsCollector(ABC):
    """
    Contrato para coleta de métricas do pipeline cognitivo.

    Implementações podem usar Prometheus, logging, materialized views, etc.
    """

    @abstractmethod
    def on_process_complete(
        self,
        result: CognitiveResult,
        metrics: dict[str, Any],
    ) -> None:
        """
        Callback invocado ao final de cada processamento.

        Args:
            result: Resultado completo do pipeline
            metrics: Dict com latências, source, fallback_reason, etc.
        """
        ...
