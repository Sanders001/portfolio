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

    def count_nodes(self) -> int:
        """Retorna a contagem total de nós na sub-árvore (este nó + descendentes)."""
        return 1 + sum(child.count_nodes() for child in self.children())

    def to_ascii_tree(self, prefix: str = "", is_last: bool = True, is_root: bool = True) -> str:
        """Gera a representação visual hierárquica em ASCII de toda a AST."""
        if hasattr(self, "value"):
            label = str(self.value)
        elif hasattr(self, "name"):
            label = self.name
        elif hasattr(self, "operator"):
            label = "IF...THEN" if getattr(self, "operator", "") == "if_then" else self.operator
        elif hasattr(self, "statements"):
            label = "BLOCK"
        else:
            label = self.node_type
            
        if is_root:
            result = label + "\n"
            child_prefix = ""
        else:
            result = prefix + ("└── " if is_last else "├── ") + label + "\n"
            child_prefix = prefix + ("    " if is_last else "│   ")
            
        children = self.children()
        for i, child in enumerate(children):
            _is_last = (i == len(children) - 1)
            result += child.to_ascii_tree(child_prefix, _is_last, is_root=False)
            
        return result


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
