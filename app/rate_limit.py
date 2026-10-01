"""Rate limiting da API pública (`/api/v1/*`) — em memória (não Redis),
válido porque o container `web` roda com 1 processo uvicorn só (ver
Dockerfile, sem `--workers`); se isso mudar no futuro, este limiter
precisa virar compartilhado (Redis) pra continuar correto.

Duas camadas:
- **Anônimo** (sem `X-API-Key` ou key inválida): limite bem baixo, por IP.
- **Com API key válida**: limite configurável por key (`ApiKey.
  rate_limit_per_hour`), bem mais alto — é o incentivo pra quem precisar
  de mais volume pedir uma key em vez de ficar sem acesso.

Janela fixa por hora (reseta no início de cada hora UTC), não é uma
sliding window perfeita, mas é simples e suficiente pro volume atual.
"""
import hashlib
import secrets
import threading
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, Request, status
from sqlmodel import select

from app.db import get_session
from app.models import ApiKey

# Bem baixo de propósito — uso anônimo da API é só pra teste/curiosidade;
# quem precisar de volume real deve pedir uma API key (ver /admin/api-keys).
ANONYMOUS_RATE_LIMIT_PER_HOUR = 30

_lock = threading.Lock()
# {identifier: (hour_bucket, count)} — hour_bucket é a hora UTC truncada
# (ex.: "2026-09-30T20"), pra resetar o contador automaticamente a cada hora.
_counters: dict[str, tuple[str, int]] = {}


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Key legível, prefixada pra facilitar identificar em logs/headers
    (ex.: `dio_live_...`), sem vazar nada sensível no prefixo em si."""
    return f"dio_live_{secrets.token_urlsafe(32)}"


def _current_hour_bucket() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")


def _check_and_increment(identifier: str, limit: int) -> tuple[bool, int]:
    bucket = _current_hour_bucket()
    with _lock:
        stored_bucket, count = _counters.get(identifier, (bucket, 0))
        if stored_bucket != bucket:
            count = 0
        count += 1
        _counters[identifier] = (bucket, count)
    return count <= limit, count


def enforce_rate_limit(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if x_api_key:
        key_hash = hash_api_key(x_api_key)
        with get_session() as session:
            api_key = session.exec(
                select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None))
            ).first()
        if api_key is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key invalida ou revogada")
        identifier = f"key:{api_key.id}"
        limit = api_key.rate_limit_per_hour
    else:
        client_ip = request.client.host if request.client else "unknown"
        identifier = f"ip:{client_ip}"
        limit = ANONYMOUS_RATE_LIMIT_PER_HOUR

    allowed, count = _check_and_increment(identifier, limit)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"limite de {limit} requisicoes/hora excedido"
                + ("" if x_api_key else " (sem API key — peça uma em /admin/api-keys pra um limite maior)")
            ),
            headers={"Retry-After": "3600"},
        )


RateLimited = Depends(enforce_rate_limit)
