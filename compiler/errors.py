"""
Erros do pipeline de compilação.
Cada erro carrega informações de localização para facilitar o debugging.
"""


class CompilerError(Exception):
    """Base para todas as exceções do compiler."""

    def __init__(self, message: str, *, source: str = "", line: int = 0, col: int = 0):
        self.source = source
        self.line = line
        self.col = col
        location = f" at line {line}, col {col}" if line else ""
        super().__init__(f"{message}{location}")


class LexError(CompilerError):
    """Token inesperado ou padrão não reconhecido."""
    pass


class ParseError(CompilerError):
    """Expectativa de token falhou ou estrutura sintática inválida."""
    pass


class SemanticError(CompilerError):
    """Identificador desconhecido, tipo incompatível, ação não registrada."""
    pass


class ExecutionError(CompilerError):
    """Erro durante execução da AST (ação falhou, tipo incorreto, divisão por zero, etc)."""
    pass
