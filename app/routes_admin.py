"""Admin UI: habilitar/desabilitar canais e ocultar marca na interface
pública, sem precisar editar YAML/redeploy. Protegida por HTTP Basic Auth
simples (credenciais em ADMIN_USER/ADMIN_PASSWORD no .env) — suficiente
pro escopo de uso pessoal de hoje (poucos admins, sem dado sensível além
do próprio painel); revisar se o projeto crescer pra múltiplos operadores.
"""
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlmodel import select

from app.config import ADMIN_PASSWORD, ADMIN_USER
from app.db import get_session
from app.models import Channel

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
