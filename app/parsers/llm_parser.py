"""Fallback de extração via LLM — só é chamado quando o regex não consegue
identificar preço + nome de produto com confiança suficiente (ver
pipeline.py). Usa qualquer endpoint compatível com a API de chat
completions da OpenAI (self-hosted, ex: Copilot Bridge, Ollama com wrapper,
ou a própria OpenAI)."""
import json
import logging

import httpx

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_ENABLED, LLM_MODEL
from app.parsers.regex_parser import ParsedOffer

logger = logging.getLogger(__name__)

_PROMPT = """Extraia os dados de uma oferta/promoção a partir do texto de um post \
de grupo de promoções (Telegram/WhatsApp). Responda SOMENTE com um JSON no \
formato abaixo, sem nenhum texto adicional:

{{
  "product_name": "<nome do produto ou null>",
  "price": <preço final em número, ou null>,
  "price_original": <preço original antes do desconto, ou null se não houver>,
  "coupon_code": "<código do cupom, ou null>"
}}

Texto do post:
---
{text}
---
"""


def parse_llm(text: str) -> ParsedOffer:
    if not LLM_ENABLED:
        return ParsedOffer()

    try:
        response = httpx.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": _PROMPT.format(text=text)}],
                "temperature": 0,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
    except Exception:  # noqa: BLE001 — fallback deliberadamente tolerante a falhas
        logger.exception("Falha ao chamar o LLM fallback, mantendo post como não-parseado")
        return ParsedOffer()

    return ParsedOffer(
        product_name=data.get("product_name"),
        price=data.get("price"),
        price_original=data.get("price_original"),
        coupon_code=data.get("coupon_code"),
        confidence=0.6,  # confiança fixa moderada — não validamos o retorno do LLM
    )
