import json
import logging
import os
import time

import redis.asyncio as redis
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Configuración
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
logger = logging.getLogger(__name__)


def load_api_keys():
    """
    Carga y valida las API Keys desde variables de entorno.
    Implementa estrategia Fail-Fast para entornos productivos.
    """
    env_keys = os.getenv("VALID_API_KEYS")
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"

    if not env_keys:
        logger.warning("VALID_API_KEYS no configurada en variables de entorno. Se dependerá exclusivamente de Redis para la validación de API Keys nuevas.")
        return {}

    try:
        return json.loads(env_keys)
    except json.JSONDecodeError as e:
        if debug_mode:
            logger.warning(f"Error decodificando VALID_API_KEYS: {e}. Usando diccionario vacío en DEBUG.")
            return {}
        error_msg = f"CRITICAL: Formato JSON inválido en VALID_API_KEYS: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)


# Inicialización Fail-Fast
VALID_API_KEYS = load_api_keys()

TIERS = {"default": 50, "premium": 1000, "internal": 99999}

# Script LUA: Rate Limit + Usage Tracking Atómico
LUA_ATOMIC_SCRIPT = """
local rate_key = KEYS[1]
local usage_key = KEYS[2]
local ttl_rate = tonumber(ARGV[1])
local ttl_usage = tonumber(ARGV[2])

-- Rate Limit Logic
local current_rate = redis.call('INCR', rate_key)
if current_rate == 1 then
    redis.call('EXPIRE', rate_key, ttl_rate)
end

-- Usage Logic
local current_usage = redis.call('INCR', usage_key)
redis.call('EXPIRE', usage_key, ttl_usage)

return {current_rate, current_usage}
"""


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        try:
            self.redis = redis.Redis(
                host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True, socket_connect_timeout=1
            )
            self.atomic_script = self.redis.register_script(LUA_ATOMIC_SCRIPT)
            # Remove blocking ping in init. Connection will be checked on first request.
            self.redis_available = True
            logger.info(f"Rate Limiting Blindado + Usage Tracking activos en {REDIS_HOST}")
        except redis.RedisError:
            self.redis_available = False
            logger.warning("Redis no disponible. Fail-open mode activo.")

    async def _validate_api_key(self, api_key: str):
        if not api_key:
            return "default", None

        # 1. Intentar validar usando Redis
        if self.redis_available:
            try:
                client_data_str = await self.redis.hget("api_keys", api_key)
                if client_data_str:
                    client_data = json.loads(client_data_str)
                    if client_data.get("active"):
                        return client_data.get("tier", "default"), api_key
            except Exception as e:
                logger.warning(f"Error accediendo a Redis para validar API Key, usando fallback: {e}")

        # 2. Fallback in-memory
        client_data = VALID_API_KEYS.get(api_key)
        if client_data and client_data.get("active"):
            return client_data.get("tier", "default"), api_key

        return None, None

    async def dispatch(self, request: Request, call_next):
        try:
            # 1. Bypass sistema
            if request.url.path in ["/", "/health", "/docs", "/openapi.json"] or request.url.path.startswith("/static"):
                return await call_next(request)

            if not self.redis_available:
                return await call_next(request)

            # 2. Autenticación
            api_key = request.headers.get("X-API-Key")
            tier, validated_client_id = await self._validate_api_key(api_key)

            if api_key and not validated_client_id:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"error": "Invalid API Key", "message": "Llave no válida o revocada."},
                )

            client_id = validated_client_id if validated_client_id else request.client.host
            limit = TIERS.get(tier, TIERS["default"])

            # 3. Lógica de Contadores (Rate Limit + Usage)
            current_minute = int(time.time() // 60)
            today = time.strftime("%Y-%m-%d")

            rate_key = f"ratelimit:{client_id}:{current_minute}"
            usage_key = f"usage:{client_id}:{today}"

            # Atomic Execution via Lua
            result = await self.atomic_script(keys=[rate_key, usage_key], args=[65, 60 * 60 * 24 * 30])

            request_count = result[0]
            usage_today = result[1]

            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(max(0, limit - request_count)),
                "X-RateLimit-Reset": str(current_minute * 60 + 60),
                "X-Usage-Today": str(usage_today),
            }

            if request_count > limit:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"error": "Rate limit exceeded", "retry_after": 60, "tier": tier},
                    headers=headers,
                )

            response = await call_next(request)

            for k, v in headers.items():
                response.headers[k] = v

            return response

        except Exception as e:
            logger.error(f"Error crítico en Middleware: {e}", exc_info=True)
            # Fallback open: Permitir que la petición continúe si el middleware falla
            try:
                return await call_next(request)
            except Exception:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Internal Middleware Error", "details": str(e)}
                )
