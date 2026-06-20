"""
Compiler Pipeline.

Orquestrador das 4 fases do compilador genérico:
Tokenize → Parse → Semantic Validate → Execute.
"""
import hashlib
from typing import Any, Callable, Optional, Tuple

from .ast_nodes import BaseNode
from .cache import CompilerCache
from .executor import BaseExecutor
from .parser import BaseParser
from .semantic import BaseSemanticAnalyzer, SemanticContext
from .tokens import BaseTokenizer, Token


class CompilerPipeline:
    """
    Coordena as ferramentas do framework de compilação de forma agnóstica a domínio.
    Gerencia cache de forma transparente a partir do source processado.
    """

    def __init__(
        self,
        tokenizer: BaseTokenizer,
        parser_factory: Callable[[list[Token]], BaseParser],
        executor: BaseExecutor,
        semantic_analyzer: Optional[BaseSemanticAnalyzer] = None,
        cache: Optional[CompilerCache] = None,
    ):
        """
        Inicializa o pipeline.

        Args:
            tokenizer: Responsável pela fase léxica.
            parser_factory: Fabrica uma instância de BaseParser por source (evitando state issues).
            executor: Responsável pela execução (AST Visitor).
            semantic_analyzer: Opcional. Analisador semântico para validar nós AST.
            cache: Opcional. Permite pular fases Tokenize+Parse (necessita de um Serializer futuramente).
        """
        self.tokenizer = tokenizer
        self.parser_factory = parser_factory
        self.executor = executor
        self.semantic_analyzer = semantic_analyzer
        self.cache = cache

    @staticmethod
    def _build_cache_key(source: str, parser_version: str = "1.0", serializer_version: str = "1.0") -> str:
        """Hash determinístico com versionamento para compor chave de cache segura."""
        content = f"{source}:{parser_version}:{serializer_version}"
        hash_ = hashlib.sha256(content.encode('utf-8')).hexdigest()
        return f"compiler_ast:{hash_}"

    def compile(self, source: str, semantic_context: Optional[SemanticContext] = None) -> BaseNode:
        """
        Fases 1, 2 e 3: Tokenize → Parse → Semantic Validate.
        """
        tokens = self.tokenizer.tokenize(source)

        parser = self.parser_factory(tokens)
        ast = parser.parse()

        if self.semantic_analyzer and semantic_context:
            self.semantic_analyzer.validate_or_raise(ast, semantic_context)

        return ast

    def compile_only(self, source: str, semantic_context: Optional[SemanticContext] = None) -> BaseNode:
        """
        Dry-run: Executa tokenização, parse e validação semântica e retorna a AST.
        """
        return self.compile(source, semantic_context)

    def run(self, source: str, context: dict, semantic_context: Optional[SemanticContext] = None) -> Tuple[Any, dict]:
        """
        Executa todas as fases:
        Tokenize → Parse → Semantic Validate → Execute

        Retorna:
            Tupla contendo o resultado da execução e a árvore de execução (Trace) como dicionário.
        """
        ast = self.compile(source, semantic_context)

        # BaseExecutor cria um root trace implícito quando invocado
        result, step = self.executor.execute(ast, context)

        return result, step.to_dict()
