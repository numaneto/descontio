"""Admin UI: habilitar/desabilitar canais e ocultar marca na interface
pública, sem precisar editar YAML/redeploy. Protegida por HTTP Basic Auth
simples (credenciais em ADMIN_USER/ADMIN_PASSWORD no .env) — suficiente
pro escopo de uso pessoal de hoje (poucos admins, sem dado sensível além
do próprio painel); revisar se o projeto crescer pra múltiplos operadores.
"""
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlmodel import select

from app.config import ADMIN_PASSWORD, ADMIN_USER
from app.db import get_session
from app.models import ApiKey, Channel, LlmUsageEvent
from app.rate_limit import generate_api_key, hash_api_key

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")
security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    if not ADMIN_USER or not ADMIN_PASSWORD:
        # Falha segura: sem credenciais configuradas, o admin fica
        # inacessível em vez de usar alguma senha padrão previsível.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="admin nao configurado")
    user_ok = secrets.compare_digest(credentials.username, ADMIN_USER)
    pass_ok = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="credenciais invalidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@router.get("/channels")
def list_channels(request: Request, _: str = Depends(require_admin)):
    with get_session() as session:
        channels = session.exec(select(Channel).order_by(Channel.label)).all()
    return templates.TemplateResponse(
        request, "admin_channels.html", {"channels": channels}
    )


@router.post("/channels/{platform}/{chat_id}/toggle-enabled")
def toggle_enabled(platform: str, chat_id: str, _: str = Depends(require_admin)):
    with get_session() as session:
        channel = session.get(Channel, (platform, chat_id))
        if channel is None:
            raise HTTPException(status_code=404, detail="canal nao encontrado")
        channel.enabled = not channel.enabled
        session.add(channel)
        session.commit()
    return RedirectResponse(url="/admin/channels", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/channels/{platform}/{chat_id}/toggle-hide-brand")
def toggle_hide_brand(platform: str, chat_id: str, _: str = Depends(require_admin)):
    with get_session() as session:
        channel = session.get(Channel, (platform, chat_id))
        if channel is None:
            raise HTTPException(status_code=404, detail="canal nao encontrado")
        channel.hide_brand = not channel.hide_brand
        session.add(channel)
        session.commit()
    return RedirectResponse(url="/admin/channels", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api-keys")
def list_api_keys(request: Request, _: str = Depends(require_admin)):
    with get_session() as session:
        keys = session.exec(select(ApiKey).order_by(ApiKey.created_at.desc())).all()
    # `new_key` só existe logo após criação (query param ?new=... de uso
    # único) — nunca é lido de volta do banco, porque não fica armazenado.
    new_key = request.query_params.get("new")
    return templates.TemplateResponse(
        request, "admin_api_keys.html", {"keys": keys, "new_key": new_key}
    )


@router.post("/api-keys/new")
def create_api_key(
    request: Request,
    label: str = Form(...),
    rate_limit_per_hour: int = Form(1000),
    _: str = Depends(require_admin),
):
    raw_key = generate_api_key()
    with get_session() as session:
        session.add(
            ApiKey(key_hash=hash_api_key(raw_key), label=label, rate_limit_per_hour=rate_limit_per_hour)
        )
        session.commit()
    # Redireciona com a key crua na query string só pra essa exibição única
    # — não fica persistida em lugar nenhum, só o hash fica no banco.
    return RedirectResponse(url=f"/admin/api-keys?new={raw_key}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/api-keys/{key_id}/revoke")
def revoke_api_key(key_id: int, _: str = Depends(require_admin)):
    with get_session() as session:
        api_key = session.get(ApiKey, key_id)
        if api_key is None:
            raise HTTPException(status_code=404, detail="key nao encontrada")
        api_key.revoked_at = datetime.utcnow()
        session.add(api_key)
        session.commit()
    return RedirectResponse(url="/admin/api-keys", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/llm-usage")
def llm_usage(request: Request, _: str = Depends(require_admin)):
    with get_session() as session:
        summary = session.exec(
            select(
                LlmUsageEvent.model,
                func.count(LlmUsageEvent.id),
                func.sum(LlmUsageEvent.prompt_tokens),
                func.sum(LlmUsageEvent.completion_tokens),
                func.sum(LlmUsageEvent.total_tokens),
                func.sum(LlmUsageEvent.estimated_cost_usd),
            ).group_by(LlmUsageEvent.model)
        ).all()
        recent = session.exec(
            select(LlmUsageEvent).order_by(LlmUsageEvent.created_at.desc()).limit(100)
        ).all()
    return templates.TemplateResponse(
        request,
        "admin_llm_usage.html",
        {"summary": summary, "recent": recent},
    )
