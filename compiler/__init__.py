"""
Compiler Framework — DSL Engine.

Framework completo de compilação para Domain-Specific Languages (DSLs).
Implementa as 4 fases clássicas: Tokenize → Parse → Semantic Validate → Execute.

Destaques:
- Pratt Parser (precedence climbing) para parsing de expressões
- AST imutável com Visitor Pattern para execução
- Trace Tree para observabilidade de execução
- Cache com abstração Redis/InMemory
- Serialização JSON-safe (sem pickle inseguro)
- Chain of Responsibility para resolução de handlers
"""

from .ast_nodes import BaseNode, LiteralNode, IdentifierNode, BinaryOpNode, UnaryOpNode, BlockNode
from .tokens import Token, BaseTokenizer
from .parser import BaseParser, PrattParser
from .executor import BaseVisitor, BaseExecutor
from .semantic import BaseSemanticAnalyzer, SemanticContext
from .pipeline import CompilerPipeline
from .cache import CompilerCache, RedisCompilerCache, InMemoryCompilerCache
from .serializer import BaseSerializer, BaseDeserializer, GenericSerializer, GenericDeserializer
from .registry import BaseProvider, SimpleCodedProvider, BaseRegistry
from .trace import TraceStep, TracePrinter
from .errors import CompilerError, LexError, ParseError, SemanticError, ExecutionError

__all__ = [
    # AST
    "BaseNode", "LiteralNode", "IdentifierNode", "BinaryOpNode", "UnaryOpNode", "BlockNode",
    # Tokenizer
    "Token", "BaseTokenizer",
    # Parser
    "BaseParser", "PrattParser",
    # Executor
    "BaseVisitor", "BaseExecutor",
    # Semantic
    "BaseSemanticAnalyzer", "SemanticContext",
    # Pipeline
    "CompilerPipeline",
    # Cache
    "CompilerCache", "RedisCompilerCache", "InMemoryCompilerCache",
    # Serializer
    "BaseSerializer", "BaseDeserializer", "GenericSerializer", "GenericDeserializer",
    # Registry
    "BaseProvider", "SimpleCodedProvider", "BaseRegistry",
    # Trace
    "TraceStep", "TracePrinter",
    # Errors
    "CompilerError", "LexError", "ParseError", "SemanticError", "ExecutionError",
]
