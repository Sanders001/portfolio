"""
Fase de Execução: Visitor Pattern e Executor.
"""
from abc import ABC
from typing import Any, Optional

from .ast_nodes import BaseNode, BinaryOpNode, BlockNode, IdentifierNode, LiteralNode, UnaryOpNode
from .errors import ExecutionError
from .trace import TraceStep


class BaseVisitor(ABC):
    """
    Visitor pattern genérico.
    Pode ser usado por Executors, Printers, ou Analyzers.
    """

    def visit(self, node: BaseNode, *args, **kwargs) -> Any:
        method_name = f"exec_{node.node_type}"
        method = getattr(self, method_name, None)
        if method is None:
            raise ExecutionError(f"No handler for node type: {node.node_type}")
        return method(node, *args, **kwargs)


class BaseExecutor(BaseVisitor):
    """
    Executor base de AST.
    Além de visitar, garante a construção automática da árvore de TraceStep.
    """

    def execute(self, node: BaseNode, context: dict, trace: Optional[TraceStep] = None) -> tuple[Any, TraceStep]:
        """
        Ponto de entrada para execução de um nó.
        Despacha para os métodos exec_*, invocando hooks antes e depois.
        """
        self.on_before_execute(node, context)

        result, step = self.visit(node, context)

        if trace is not None:
            trace.children.append(step)

        self.on_after_execute(node, result, step)

        return result, step

    # ── Hooks de Extensibilidade ─────────────────────────────────

    def on_before_execute(self, node: BaseNode, context: dict) -> None:
        """Chamado antes de executar um nó. Ideal para logging prévio."""
        pass

    def on_after_execute(self, node: BaseNode, result: Any, step: TraceStep) -> None:
        """Chamado após a execução de um nó. Ideal para enriquecer metadados no trace."""
        pass

    # ── Handlers Abstratos / Padrão (devem ser sobreescritos pela DSL) ─

    def exec_literal(self, node: LiteralNode, context: dict) -> tuple[Any, TraceStep]:
        step = TraceStep(node_type="literal", value=node.value, result=node.value)
        return node.value, step

    def exec_identifier(self, node: IdentifierNode, context: dict) -> tuple[Any, TraceStep]:
        if node.name not in context:
            raise ExecutionError(f"Identifier not found in context: {node.name}")

        value = context.get(node.name)
        step = TraceStep(node_type="identifier", value=node.name, result=value)
        return value, step

    def exec_binary_op(self, node: BinaryOpNode, context: dict) -> tuple[Any, TraceStep]:
        """
        A execução padrão de um binário depende da DSL, pois envolve
        definir os operadores permitidos. Um parser DSL sobreescreve este método.
        """
        raise NotImplementedError("The DSL must implement binary operation execution.")

    def exec_unary_op(self, node: UnaryOpNode, context: dict) -> tuple[Any, TraceStep]:
        """A execução de operador unário deve ser definida pela DSL."""
        raise NotImplementedError("The DSL must implement unary operation execution.")

    def exec_block(self, node: BlockNode, context: dict) -> tuple[Any, TraceStep]:
        """Executa sequencialmente todos os statements."""
        results = []
        children_traces = []

        for statement in node.statements:
            res, t_step = self.execute(statement, context)
            results.append(res)
            children_traces.append(t_step)

        step = TraceStep(node_type="block", result=results, children=children_traces)
        return results, step
