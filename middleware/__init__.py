"""
Middleware Stack — Production-ready middlewares for FastAPI/Starlette.

Includes:
- Customs (payload sanitization + audit logging for external integrations)
- Idempotency (duplicate request prevention via Redis distributed locks)
- Rate Limiter (sliding window with Redis sorted sets)
"""
