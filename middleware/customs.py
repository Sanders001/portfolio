"""
Customs — Middleware de Inspeção para Integrações Externas.

Toda requisição de/para integrações externas passa pela Alfândega antes
de entrar no sistema.

Responsabilidades:
1. Validação de payload (tamanho máximo)
2. Sanitização (remoção de campos perigosos)
3. Logging de auditoria (o que entra e sai)
4. Headers de rastreabilidade
"""
import json
import logging
import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Campos que nunca devem ser aceitos de fontes externas
FORBIDDEN_FIELDS = {
    "__import__", "__builtins__", "eval", "exec",
    "__class__", "__subclasses__",
}

# Tamanho máximo de payload aceito (bytes)
MAX_PAYLOAD_SIZE = 1_048_576  # 1 MB


class CustomsMiddleware(BaseHTTPMiddleware):
    """
    Middleware de inspeção de fronteira — inspeciona o que entra e sai da API.

    Aplica-se automaticamente a todas as rotas de integração externa.
    Para rotas internas, faz bypass transparente.

    Args:
        app: Aplicação ASGI.
        border_prefixes: Tupla de prefixos de rota que são considerados "fronteira".
        max_payload_size: Tamanho máximo de payload aceito em bytes.
        forbidden_fields: Set de campos proibidos em payloads JSON.
    """

    def __init__(
        self,
        app,
        border_prefixes: tuple[str, ...] = ("/api/v1/integrations",),
        max_payload_size: int = MAX_PAYLOAD_SIZE,
        forbidden_fields: Optional[set[str]] = None,
    ):
        super().__init__(app)
        self.border_prefixes = border_prefixes
        self.max_payload_size = max_payload_size
        self.forbidden_fields = forbidden_fields or FORBIDDEN_FIELDS

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Bypass para rotas internas (não são fronteira)
        if not self._is_border_route(path):
            return await call_next(request)

        # ── INSPEÇÃO DE ENTRADA ───────────────────────────────
        started = time.time()
        method = request.method
        integration_source = self._identify_source(request)

        logger.info(
            f"[customs] Incoming: {method} {path} | source={integration_source}"
        )

        # 1. Validar tamanho do payload
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_payload_size:
            logger.warning(
                f"[customs] Payload exceeds limit: {content_length} bytes "
                f"(max: {self.max_payload_size})"
            )
            return JSONResponse(
                status_code=413,
                content={
                    "detail": "Payload exceeds maximum allowed size",
                    "max_bytes": self.max_payload_size,
                },
            )

        # 2. Sanitizar payload (POST/PUT/PATCH)
        if method in ("POST", "PUT", "PATCH"):
            violation = await self._sanitize_payload(request)
            if violation:
                logger.warning(
                    f"[customs] Payload contains forbidden fields: {violation}"
                )
                return JSONResponse(
                    status_code=400,
                    content={
                        "detail": "Payload contains forbidden fields",
                        "forbidden_fields": violation,
                    },
                )

        # ── PROCESSAR REQUISIÇÃO ──────────────────────────────
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"[customs] Error processing {path}: {e}")
            raise

        # ── INSPEÇÃO DE SAÍDA ─────────────────────────────────
        duration_ms = int((time.time() - started) * 1000)

        logger.info(
            f"[customs] Outgoing: {method} {path} | "
            f"status={response.status_code} | {duration_ms}ms | "
            f"source={integration_source}"
        )

        # Adicionar headers de auditoria
        response.headers["X-Customs-Inspected"] = "true"
        response.headers["X-Customs-Duration-Ms"] = str(duration_ms)
        response.headers["X-Customs-Source"] = integration_source

        return response

    # ── Helpers ────────────────────────────────────────────────

    def _is_border_route(self, path: str) -> bool:
        """Verifica se a rota é uma fronteira (integração externa)."""
        return any(path.startswith(prefix) for prefix in self.border_prefixes)

    @staticmethod
    def _identify_source(request: Request) -> str:
        """Identifica a fonte da integração a partir do path."""
        path = request.url.path
        # Extract the integration name from the path (e.g. /api/v1/integrations/stripe → stripe)
        parts = path.split("/")
        for i, part in enumerate(parts):
            if part == "integrations" and i + 1 < len(parts):
                return parts[i + 1]
        return "unknown"

    async def _sanitize_payload(self, request: Request) -> Optional[list[str]]:
        """
        Verifica se o payload contém campos proibidos.
        Retorna lista de campos proibidos encontrados, ou None se limpo.
        """
        try:
            body = await request.body()
            if not body:
                return None

            # Tenta parsear como JSON
            try:
                data = json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None  # Não é JSON, deixa passar (pode ser multipart)

            # Verificação recursiva de campos proibidos
            violations: list[str] = []
            _check_forbidden_keys(data, violations, self.forbidden_fields)

            return violations if violations else None
        except Exception:
            return None  # Em caso de erro na leitura, não bloqueia


def _check_forbidden_keys(
    data: object,
    violations: list[str],
    forbidden: set[str],
    prefix: str = "",
) -> None:
    """Verifica recursivamente se há campos proibidos no payload."""
    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if key.lower() in forbidden:
                violations.append(full_key)
            _check_forbidden_keys(value, violations, forbidden, full_key)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _check_forbidden_keys(item, violations, forbidden, f"{prefix}[{i}]")
