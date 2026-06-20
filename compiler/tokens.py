"""
Fase Léxica: Tokenização.
"""
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .errors import LexError


@dataclass(frozen=True)
class Token:
    """
    Representação imutável de um elemento léxico.
    """
    type: str
    value: Any
    line: int = 0
    col: int = 0


class BaseTokenizer(ABC):
    """
    Contrato base para Tokenizers.
    Transforma texto puro em uma sequência de Tokens.
    """

    @abstractmethod
    def tokenize(self, source: str) -> list[Token]:
        """
        Analisa o texto e retorna a lista de tokens.
        Deve obrigatoriamente terminar com um token 'EOF'.
        """
        pass

    def normalize(self, text: str) -> str:
        """
        Hook para normalização de texto (ex: aliases, lowercasing)
        antes do regex processar.
        """
        return text

    def _regex_tokenize(self, source: str, spec: list[tuple[str, str]]) -> list[Token]:
        """
        Implementação reutilizável de tokenização via regex.

        Args:
            source: Texto a ser tokenizado.
            spec: Lista de tuplas (nome_do_token, regex_pattern).

        Returns:
            Lista de Tokens finalizada com EOF.

        Raises:
            LexError: Se encontrar um padrão não reconhecido.
        """
        tok_regex = "|".join(f"(?P<{pair[0]}>{pair[1]})" for pair in spec)
        get_token = re.compile(tok_regex).match
        line_num = 1
        line_start = 0
        pos = 0
        tokens = []

        normalized_source = self.normalize(source)
        length = len(normalized_source)

        while pos < length:
            match = get_token(normalized_source, pos)
            if not match:
                char = normalized_source[pos]
                # Pula whitespace genérico se não foi especificado na gramática
                if char.isspace():
                    if char == '\n':
                        line_num += 1
                        line_start = pos + 1
                    pos += 1
                    continue
                col = pos - line_start
                raise LexError(f"Unexpected character: {char!r}", source=source, line=line_num, col=col)

            type_ = match.lastgroup
            value = match.group(type_)

            # Se for whitespace capturado explicitamente ou newline (para contagem)
            if type_ == "NEWLINE" or type_ == "WS" or type_ == "SKIP":
                if value.startswith('\n'):
                    line_start = pos + len(value)
                    line_num += 1
                pos = match.end()
                continue

            col = pos - line_start
            tokens.append(Token(type=type_, value=value, line=line_num, col=col))
            pos = match.end()

        tokens.append(Token(type="EOF", value=None, line=line_num, col=pos - line_start))
        return tokens
