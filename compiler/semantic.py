"""
Fase Semântica: Validação.

Garante que a AST gerada faz sentido antes da execução.
Verifica se variáveis existem, se tipos são compatíveis e se ações estão registradas.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .ast_nodes import BaseNode
from .errors import SemanticError


@dataclass(frozen=True)
class SemanticContext:
    """
    Contexto tipado para validação semântica.
    Passado ao analyzer para validar se a AST está coerente com as regras de negócio.
    """
    identifiers: dict[str, Any] = field(default_factory=dict)
    actions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseSemanticAnalyzer(ABC):
    """
    Contrato base para análise semântica.
    """

    @abstractmethod
    def analyze(self, node: BaseNode, context: SemanticContext) -> list[SemanticError]:
        """
        Valida a AST contra um contexto semântico.
        Deve retornar uma lista vazia se a AST for válida.
        """
        pass

    def validate_or_raise(self, node: BaseNode, context: SemanticContext) -> None:
        """
        Atalho que executa a análise e levanta a primeira exceção encontrada.
        """
        errors = self.analyze(node, context)
        if errors:
            raise errors[0]
