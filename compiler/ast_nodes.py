"""
Árvore Sintática Abstrata (AST) Genérica.

Define as estruturas imutáveis que representam o código analisado.
As subclasses genéricas cobrem os blocos de construção comuns de DSLs.
Nós de domínio (ex: MaskNode, SendEmailNode) devem herdar de BaseNode.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class BaseNode(ABC):
    """Contrato base para qualquer nó AST."""

    @property
    @abstractmethod
    def node_type(self) -> str:
        """Retorna o tipo do nó como string para serialização e dispatch."""
        pass

    @abstractmethod
    def children(self) -> list["BaseNode"]:
        """Retorna os nós filhos diretos para travessia em árvore."""
        pass


@dataclass(frozen=True)
class LiteralNode(BaseNode):
    """
    Valor constante: string, número, booleano, null.
    """
    value: Any

    @property
    def node_type(self) -> str:
        return "literal"

    def children(self) -> list[BaseNode]:
        return []


@dataclass(frozen=True)
class IdentifierNode(BaseNode):
    """
    Referência a uma variável, campo ou contexto.
    """
    name: str

    @property
    def node_type(self) -> str:
        return "identifier"

    def children(self) -> list[BaseNode]:
        return []


@dataclass(frozen=True)
class BinaryOpNode(BaseNode):
    """
    Operação com dois operandos.
    Exemplos: 'and', 'or', '==', '>', 'is', 'contains'
    """
    operator: str
    left: BaseNode
    right: BaseNode

    @property
    def node_type(self) -> str:
        return "binary_op"

    def children(self) -> list[BaseNode]:
        return [self.left, self.right]


@dataclass(frozen=True)
class UnaryOpNode(BaseNode):
    """
    Operação com um operando.
    Exemplos: 'not', '-', '+'
    """
    operator: str
    operand: BaseNode

    @property
    def node_type(self) -> str:
        return "unary_op"

    def children(self) -> list[BaseNode]:
        return [self.operand]


@dataclass(frozen=True)
class BlockNode(BaseNode):
    """
    Sequência ordenada de nós (multi-ação ou corpo de funções/if).
    Usa tupla para manter imutabilidade.
    """
    statements: tuple[BaseNode, ...]

    @property
    def node_type(self) -> str:
        return "block"

    def children(self) -> list[BaseNode]:
        return list(self.statements)
