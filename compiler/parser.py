"""
Fase Sintática: Parsing.

Implementação do algoritmo Pratt Parser (precedence climbing) genérico.
Permite definir DSLs que respeitem precedência matemática ou lógica natural.
"""
from abc import ABC, abstractmethod

from .ast_nodes import BaseNode
from .errors import ParseError
from .tokens import Token


class BaseParser(ABC):
    """Contrato base para parsers."""

    @abstractmethod
    def parse(self) -> BaseNode:
        """Converte a lista de tokens consumida em uma AST."""
        pass


class PrattParser(BaseParser):
    """
    Pratt Parser — algoritmo de precedência de operadores.

    Consumidores estendem esta classe e implementam `nud`, `led` e
    `get_precedence` para associar tokens às suas regras gramaticais.
    """

    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos = 0
        self._current = tokens[0] if tokens else Token("EOF", None)

    # ── Utilitários de Movimentação ──────────────────────────────

    def advance(self) -> Token:
        """Avança para o próximo token e retorna o atual."""
        prev = self._current
        if self._pos < len(self._tokens) - 1:
            self._pos += 1
            self._current = self._tokens[self._pos]
        return prev

    def match(self, expected_type: str) -> bool:
        """Se o token atual for do tipo esperado, avança e retorna True."""
        if self._current.type == expected_type:
            self.advance()
            return True
        return False

    def expect(self, expected_type: str) -> Token:
        """Como match(), mas levanta ParseError se não encontrar o tipo."""
        if self._current.type == expected_type:
            return self.advance()
        raise ParseError(
            f"Expected {expected_type}, found {self._current.type}",
            line=self._current.line, col=self._current.col
        )

    def peek(self) -> Token:
        """Retorna o token atual sem avançar."""
        return self._current

    def is_at_end(self) -> bool:
        return self._current.type == "EOF"

    # ── Core do Pratt Parser ─────────────────────────────────────

    def parse(self) -> BaseNode:
        """Ponto de entrada principal."""
        node = self.expression(0)
        if not self.is_at_end():
            raise ParseError(
                f"Unconsumed token after expression: {self._current.type}",
                line=self._current.line, col=self._current.col
            )
        return node

    def expression(self, rbp: int = 0) -> BaseNode:
        """
        Parsa uma expressão garantindo precedência.
        rbp = Right Binding Power.
        """
        token = self.advance()
        left = self.nud(token)

        while rbp < self.get_precedence(self._current):
            token = self.advance()
            left = self.led(token, left)

        return left

    # ── Métodos a serem implementados pela DSL (Hooks) ───────────

    @abstractmethod
    def nud(self, token: Token) -> BaseNode:
        """
        Null Denotation.
        Processa tokens que NÃO dependem de uma expressão à esquerda.
        (ex: Literais, Identificadores, Operadores Unários de prefixo).
        """
        pass

    @abstractmethod
    def led(self, token: Token, left: BaseNode) -> BaseNode:
        """
        Left Denotation.
        Processa tokens que DEPENDEM de uma expressão à esquerda.
        (ex: Operadores Binários +, -, *, /, and, or).
        """
        pass

    @abstractmethod
    def get_precedence(self, token: Token) -> int:
        """
        Retorna o "Binding Power" de um token.
        Quanto maior o número, mais forte ele se liga aos operandos vizinhos.
        """
        pass
