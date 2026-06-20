"""
Example: Building a Rules DSL with the Compiler Framework.

Demonstrates how to build a concrete DSL on top of the generic compiler,
implementing a simple rule language:

    IF age > 18 AND status == "active" THEN approve

This example implements:
- A concrete Tokenizer (RuleTokenizer)
- A concrete Parser (RuleParser) extending PrattParser
- A concrete Executor (RuleExecutor) extending BaseExecutor
- Full pipeline execution with trace output
"""
from compiler import (
    BaseExecutor,
    BaseNode,
    BinaryOpNode,
    BlockNode,
    CompilerPipeline,
    IdentifierNode,
    LiteralNode,
    PrattParser,
    Token,
    BaseTokenizer,
    TraceStep,
    TracePrinter,
    ParseError,
)
from typing import Any


# ═══════════════════════════════════════════════════════════════
# 1. TOKENIZER — Define os tokens da nossa DSL
# ═══════════════════════════════════════════════════════════════

class RuleTokenizer(BaseTokenizer):
    """Tokenizer para a linguagem de regras."""

    SPEC = [
        ("NUMBER",   r"\d+(\.\d+)?"),
        ("STRING",   r'"[^"]*"'),
        ("AND",      r"\b[Aa][Nn][Dd]\b"),
        ("OR",       r"\b[Oo][Rr]\b"),
        ("NOT",      r"\b[Nn][Oo][Tt]\b"),
        ("IF",       r"\b[Ii][Ff]\b"),
        ("THEN",     r"\b[Tt][Hh][Ee][Nn]\b"),
        ("TRUE",     r"\b[Tt][Rr][Uu][Ee]\b"),
        ("FALSE",    r"\b[Ff][Aa][Ll][Ss][Ee]\b"),
        ("EQ",       r"=="),
        ("NEQ",      r"!="),
        ("GTE",      r">="),
        ("LTE",      r"<="),
        ("GT",       r">"),
        ("LT",       r"<"),
        ("LPAREN",   r"\("),
        ("RPAREN",   r"\)"),
        ("IDENT",    r"[a-zA-Z_]\w*"),
        ("WS",       r"\s+"),
    ]

    def tokenize(self, source: str) -> list[Token]:
        return self._regex_tokenize(source, self.SPEC)


# ═══════════════════════════════════════════════════════════════
# 2. PARSER — Pratt Parser concreto para a DSL de regras
# ═══════════════════════════════════════════════════════════════

class RuleParser(PrattParser):
    """
    Parser concreto que implementa os hooks do PrattParser
    para a linguagem de regras.
    """

    # Binding Power (precedência) para cada operador
    PRECEDENCES = {
        "OR": 10,
        "AND": 20,
        "EQ": 30, "NEQ": 30,
        "GT": 40, "LT": 40, "GTE": 40, "LTE": 40,
    }

    def get_precedence(self, token: Token) -> int:
        return self.PRECEDENCES.get(token.type, 0)

    def nud(self, token: Token) -> BaseNode:
        """Processa tokens que iniciam uma expressão."""
        if token.type == "NUMBER":
            val = float(token.value) if "." in token.value else int(token.value)
            return LiteralNode(value=val)

        if token.type == "STRING":
            return LiteralNode(value=token.value.strip('"'))

        if token.type == "TRUE":
            return LiteralNode(value=True)

        if token.type == "FALSE":
            return LiteralNode(value=False)

        if token.type == "IDENT":
            return IdentifierNode(name=token.value)

        if token.type == "NOT":
            from compiler.ast_nodes import UnaryOpNode
            operand = self.expression(50)  # Alta precedência
            return UnaryOpNode(operator="not", operand=operand)

        if token.type == "LPAREN":
            expr = self.expression(0)
            self.expect("RPAREN")
            return expr

        if token.type == "IF":
            condition = self.expression(0)
            self.expect("THEN")
            action = self.expression(0)
            return BinaryOpNode(operator="if_then", left=condition, right=action)

        raise ParseError(
            f"Unexpected token: {token.type} ({token.value})",
            line=token.line, col=token.col,
        )

    def led(self, token: Token, left: BaseNode) -> BaseNode:
        """Processa operadores binários (infixos)."""
        operator_map = {
            "AND": "and", "OR": "or",
            "EQ": "==", "NEQ": "!=",
            "GT": ">", "LT": "<", "GTE": ">=", "LTE": "<=",
        }

        if token.type in operator_map:
            right = self.expression(self.PRECEDENCES[token.type])
            return BinaryOpNode(
                operator=operator_map[token.type],
                left=left,
                right=right,
            )

        raise ParseError(
            f"Unexpected infix token: {token.type}",
            line=token.line, col=token.col,
        )


# ═══════════════════════════════════════════════════════════════
# 3. EXECUTOR — Visitor que avalia a AST com um contexto
# ═══════════════════════════════════════════════════════════════

class RuleExecutor(BaseExecutor):
    """Executor concreto que avalia expressões da DSL de regras."""

    BINARY_OPS = {
        "==":  lambda a, b: a == b,
        "!=":  lambda a, b: a != b,
        ">":   lambda a, b: a > b,
        "<":   lambda a, b: a < b,
        ">=":  lambda a, b: a >= b,
        "<=":  lambda a, b: a <= b,
        "and": lambda a, b: a and b,
        "or":  lambda a, b: a or b,
    }

    def exec_binary_op(self, node: BinaryOpNode, context: dict) -> tuple[Any, TraceStep]:
        # Caso especial: IF ... THEN ...
        if node.operator == "if_then":
            cond_result, cond_trace = self.execute(node.left, context)
            if cond_result:
                action_result, action_trace = self.execute(node.right, context)
                step = TraceStep(
                    node_type="if_then",
                    value="condition=True",
                    result=action_result,
                    children=[cond_trace, action_trace],
                )
                return action_result, step
            else:
                step = TraceStep(
                    node_type="if_then",
                    value="condition=False",
                    result=None,
                    children=[cond_trace],
                )
                return None, step

        # Operadores binários padrão
        left_val, left_trace = self.execute(node.left, context)
        right_val, right_trace = self.execute(node.right, context)

        op_func = self.BINARY_OPS.get(node.operator)
        if not op_func:
            raise ValueError(f"Unknown operator: {node.operator}")

        result = op_func(left_val, right_val)

        step = TraceStep(
            node_type="binary_op",
            value=f"{left_val} {node.operator} {right_val}",
            result=result,
            children=[left_trace, right_trace],
        )
        return result, step

    def exec_unary_op(self, node, context: dict) -> tuple[Any, TraceStep]:
        if node.operator == "not":
            val, child_trace = self.execute(node.operand, context)
            result = not val
            step = TraceStep(
                node_type="unary_op",
                value=f"not {val}",
                result=result,
                children=[child_trace],
            )
            return result, step
        raise ValueError(f"Unknown unary operator: {node.operator}")


# ═══════════════════════════════════════════════════════════════
# 4. DEMO — Executando o pipeline completo
# ═══════════════════════════════════════════════════════════════

def main():
    # Montar o pipeline
    pipeline = CompilerPipeline(
        tokenizer=RuleTokenizer(),
        parser_factory=lambda tokens: RuleParser(tokens),
        executor=RuleExecutor(),
    )

    # Definir exemplos de regras
    examples = [
        {
            "rule": 'age > 18 AND status == "active"',
            "context": {"age": 25, "status": "active"},
        },
        {
            "rule": 'score >= 80 OR vip == True',
            "context": {"score": 65, "vip": True},
        },
        {
            "rule": 'IF age > 18 AND status == "active" THEN approved',
            "context": {"age": 25, "status": "active", "approved": True},
        },
        {
            "rule": 'NOT (age < 18)',
            "context": {"age": 25},
        },
        {
            "rule": '(price > 100 AND quantity >= 5) OR discount == True',
            "context": {"price": 50, "quantity": 3, "discount": True},
        },
    ]

    printer = TracePrinter()

    for i, example in enumerate(examples, 1):
        print(f"\n{'='*60}")
        print(f"Example {i}: {example['rule']}")
        print(f"Context: {example['context']}")
        print(f"{'='*60}")

        result, trace = pipeline.run(example["rule"], example["context"])

        print(f"\n  Result: {result}")
        print(f"\n  Execution Trace:")
        # Reconstruct TraceStep from dict (to_dict uses "type", dataclass uses "node_type")
        if isinstance(trace, dict):
            trace_step = _dict_to_trace(trace)
        else:
            trace_step = trace
        printer.print(trace_step, level=2)


def _dict_to_trace(d: dict) -> TraceStep:
    """Recursively converts a trace dict back to TraceStep objects."""
    children = [_dict_to_trace(c) for c in d.get("children", [])]
    return TraceStep(
        node_type=d.get("type", "unknown"),
        value=d.get("value"),
        result=d.get("result"),
        children=children,
        duration_ms=d.get("duration_ms"),
        metadata=d.get("metadata", {}),
    )


if __name__ == "__main__":
    main()
