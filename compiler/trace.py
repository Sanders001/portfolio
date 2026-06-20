"""
Observabilidade: Trace Tree.

Define a estrutura de dados para rastrear a execução de uma AST.
Garante auditoria de qual nó gerou qual resultado.
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TraceStep:
    """
    Passo de execução único de um nó da AST.
    Organizado em formato de árvore para representar a pilha de execução.
    """
    node_type: str
    value: Any = None
    result: Any = None
    children: list["TraceStep"] = field(default_factory=list)
    timestamp: Optional[float] = None
    duration_ms: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serializa o TraceStep para JSON."""
        data = {
            "type": self.node_type,
            "result": self.result
        }

        if self.value is not None:
            data["value"] = self.value

        if self.children:
            data["children"] = [child.to_dict() for child in self.children]

        if self.duration_ms is not None:
            data["duration_ms"] = self.duration_ms

        if self.metadata:
            data["metadata"] = self.metadata

        return data


class TracePrinter:
    """
    Utilitário para impressão da árvore de execução no terminal.
    """

    def print(self, step: TraceStep, level: int = 0) -> None:
        indent = "  " * level
        line = f"{indent}{step.node_type.upper()}"

        if step.value is not None:
            line += f"({step.value})"

        if step.result is not None:
            line += f" → {step.result}"

        print(line)

        for child in step.children:
            self.print(child, level + 1)
