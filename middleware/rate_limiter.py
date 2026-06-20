"""
Rate Limiter — Sliding Window com Redis Sorted Sets.

Implementa rate limiting por rota usando o algoritmo sliding window,
que é mais preciso que fixed window e evita rajadas na borda da janela.

Algoritmo:
1. Adiciona timestamp atual ao sorted set da chave
2. Remove entradas fora da janela (mais antigas que window_seconds)
3. Conta quantas entradas restam
4. Se > max_requests → bloqueado (429)
5. Define TTL no key para auto-limpeza
"""
import time
from typing import Optional

from fastapi import status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiter via Redis sliding window.

    Permite definir regras de rate limit por prefixo de rota.

    Args:
        app: Aplicação ASGI.
        redis_client: Cliente Redis síncrono.
        rules: Lista de regras, cada uma sendo um dict com:
            - prefix (str): Prefixo de rota (ex: "/api/v1/auth")
            - max_requests (int): Máximo de requests na janela
            - window (int): Janela em segundos
            - key_suffix (str): Sufixo para a chave Redis (ex: "auth", "webhook")

    Example:
        rules = [
            {"prefix": "/api/v1/auth", "max_requests": 10, "window": 60, "key_suffix": "auth"},
            {"prefix": "/api/v1/webhook", "max_requests": 300, "window": 60, "key_suffix": "webhook"},
            {"prefix": "/api/v1", "max_requests": 100, "window": 60, "key_suffix": "api"},
        ]
        app.add_middleware(RateLimiterMiddleware, redis_client=redis, rules=rules)
    """
    def __init__(
        self,
        app,
        redis_client,
        rules: Optional[list[dict]] = None,
    ):
        super().__init__(app)
        self.redis = redis_client
        self.rules = rules or [
            {"prefix": "/api/v1/auth", "max_requests": 10, "window": 60, "key_suffix": "auth"},
            {"prefix": "/api/v1/webhook", "max_requests": 300, "window": 60, "key_suffix": "webhook"},
            {"prefix": "/api/v1", "max_requests": 100, "window": 60, "key_suffix": "api"},
        ]

    def _is_rate_limited(self, key: str, max_requests: int, window: int) -> bool:
        """
        Verifica se a chave está rate-limited usando sliding window.

        Usa ZADD + ZREMRANGEBYSCORE + ZCARD em pipeline para eficiência.
        """
        current_time = time.time()
        pipeline = self.redis.pipeline()

        # Add current request timestamp
        pipeline.zadd(key, {str(current_time): current_time})
        # Remove old requests outside the window
        pipeline.zremrangebyscore(key, 0, current_time - window)
        # Count requests in current window
        pipeline.zcard(key)
        # Set expire so keys don't live forever
        pipeline.expire(key, window)

        results = pipeline.execute()
        request_count = results[2]

        return request_count > max_requests

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        # Check rules in order (first match wins)
        for rule in self.rules:
            if path.startswith(rule["prefix"]):
                key = f"rate_limit:{rule['key_suffix']}:{client_ip}"
                if self._is_rate_limited(key, rule["max_requests"], rule["window"]):
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "detail": "Rate limit exceeded. Please try again later.",
                            "retry_after_seconds": rule["window"],
                        }
                    )
                break  # First matching rule applies

        response = await call_next(request)
        return response
