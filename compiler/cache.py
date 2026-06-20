"""
Utilitários de Cache para AST Compilada.
"""
from abc import ABC, abstractmethod
from typing import Optional


class CompilerCache(ABC):
    """Contrato base para cache de artefatos do compilador."""

    @abstractmethod
    def get(self, key: str) -> Optional[bytes]:
        """Recupera payload em bytes a partir da key."""
        pass

    @abstractmethod
    def set(self, key: str, payload: bytes, ttl: int = 3600) -> None:
        """Salva payload associado a uma key com tempo de expiração."""
        pass

    @abstractmethod
    def invalidate(self, key: str) -> None:
        """Invalida a key do cache."""
        pass


class RedisCompilerCache(CompilerCache):
    """
    Implementação de cache usando cliente Redis.
    """
    def __init__(self, redis_client):
        self.redis = redis_client

    def get(self, key: str) -> Optional[bytes]:
        data = self.redis.get(key)
        return data if data else None

    def set(self, key: str, payload: bytes, ttl: int = 3600) -> None:
        self.redis.set(key, payload, ex=ttl)

    def invalidate(self, key: str) -> None:
        self.redis.delete(key)


class InMemoryCompilerCache(CompilerCache):
    """
    Implementação simples em memória para testes e desenvolvimento.
    Sem suporte a TTL efetivo no runtime sem background worker.
    """
    def __init__(self):
        self._cache: dict[str, bytes] = {}

    def get(self, key: str) -> Optional[bytes]:
        return self._cache.get(key)

    def set(self, key: str, payload: bytes, ttl: int = 3600) -> None:
        # Note: TTL is not actively managed in this mock implementation
        self._cache[key] = payload

    def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)
