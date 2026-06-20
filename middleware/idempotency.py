"""
Idempotency — Prevenção de operações duplicadas via Redis.

Usa lock distribuído (SET NX) com TTL para garantir que uma mesma
requisição (mesmo user + endpoint + payload) seja executada no máximo uma vez
dentro de uma janela de tempo.

Fluxo:
1. Calcula hash do (user_id + endpoint + payload)
2. Verifica se já existe no Redis
   - Se "done" → retorna resultado cacheado
   - Se "processing" → retorna status de processamento
3. Adquire lock via SET NX (atômico)
   - Se falha → duplicata detectada
4. Executa a função
5. Armazena resultado no Redis com TTL
6. Em caso de erro → limpa a chave (permite retry)
"""
import hashlib
import json
from functools import wraps
from typing import Callable, Optional

from fastapi import Request
from fastapi.encoders import jsonable_encoder


def idempotence(
    endpoint: str,
    ttl: int = 10,
    key_builder: Optional[Callable] = None,
    redis_client=None,
):
    """
    Decorator de idempotência para endpoints FastAPI.

    Args:
        endpoint: Identificador do endpoint (ex: "create_order").
        ttl: Tempo de vida do cache em segundos.
        key_builder: Função customizada para gerar a chave.
            Recebe (request: Request) e retorna str.
        redis_client: Cliente Redis. Se None, deve ser configurado antes do uso.

    Usage:
        @idempotence(endpoint="create_order", ttl=10, redis_client=redis)
        async def create_order(request: Request, payload: OrderCreate):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Resolve redis client (allows late binding)
            _redis = redis_client
            if _redis is None:
                raise RuntimeError(
                    "Redis client not configured for idempotency. "
                    "Pass redis_client to @idempotence()."
                )

            request: Request = kwargs.get("request")
            if not request:
                raise RuntimeError("Request not found in idempotency decorator kwargs")

            # ========================
            # USER
            # ========================
            user = kwargs.get("current_user") or getattr(request.state, "user", None)
            user_id = getattr(user, "id", "anonymous")

            # ========================
            # PAYLOAD
            # ========================
            payload = {}

            if request.method in ["POST", "PUT", "PATCH"]:
                body_bytes = getattr(request, "_body", None)

                if body_bytes is None:
                    try:
                        body_bytes = await request.body()
                    except RuntimeError:
                        body_bytes = None

                payload = json.loads(body_bytes) if body_bytes else {}

            # ========================
            # KEY
            # ========================
            if key_builder:
                key = key_builder(request)
            else:
                key = _generate_idempotency_key(user_id, endpoint, payload)

            # ========================
            # CHECK CACHE
            # ========================
            cached = _redis.get(key)

            if cached:
                data = json.loads(cached)

                if data.get("status") == "done":
                    return data.get("response")

                if data.get("status") == "processing":
                    return {
                        "status": "processing",
                        "message": "Request is being processed"
                    }

            # ========================
            # LOCK (NX)
            # ========================
            was_set = _redis.set(
                key,
                json.dumps({"status": "processing"}),
                ex=ttl,
                nx=True
            )

            if not was_set:
                return {
                    "status": "duplicated",
                    "message": "Duplicate request detected"
                }

            # ========================
            # EXECUTION
            # ========================
            try:
                response = await func(*args, **kwargs)

                # Salva resultado
                _redis.set(
                    key,
                    json.dumps({
                        "status": "done",
                        "response": jsonable_encoder(response)
                    }),
                    ex=ttl
                )

                return response

            except Exception as e:
                # Limpa chave em caso de erro (permite retry)
                _redis.delete(key)
                raise e

        return wrapper
    return decorator


def _generate_idempotency_key(user_id: str, endpoint: str, payload: dict) -> str:
    """
    Gera uma chave de idempotência determinística baseada em
    user_id + endpoint + payload hash.
    """
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    raw = f"{user_id}:{endpoint}:{payload_str}"
    hash_ = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"idempotency:{endpoint}:{hash_}"
