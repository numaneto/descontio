"""Classificação e normalização via endpoint OpenAI-compatible."""
import json
import logging
import re

import httpx

from app.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_ENABLED,
    LLM_INPUT_COST_PER_MILLION,
    LLM_MODEL,
    LLM_OUTPUT_COST_PER_MILLION,
)
from app.db import get_session
from app.models import LlmUsageEvent
from app.money import cents_to_amount, parse_brl_to_cents
from app.parsers.regex_parser import ParsedOffer

logger = logging.getLogger(__name__)

ALLOWED_CATEGORIES = (
    "informatica",
    "celulares",
    "eletronicos",
    "games",
    "eletrodomesticos",
    "casa-cozinha",
    "moda-beleza",
    "mercado",
    "esporte-lazer",
    "ferramentas-automotivo",
    "viagens-servicos",
    "outros",
)

_PROMPT = """Você é o Offer Formatter do descont.io. Analise uma entrada bruta \
recebida de uma fonte privada. Decida se ela anuncia uma oferta comercial \
acionável. Conversa, notícia, pedido de ajuda, enquete, aviso do canal, sorteio \
sem compra e mensagem sem produto/link não são ofertas.

Não copie nome, bordão, convite, hashtag ou propaganda da fonte. Produza somente \
os dados da oferta, de forma agnóstica à origem. Responda SOMENTE com JSON:

{{
  "is_offer": true ou false,
  "rejection_reason": "<motivo curto se não for oferta, senão null>",
  "product_name": "<nome limpo e específico do produto/serviço ou null>",
  "price": <preço final em número, ou null>,
  "price_original": <preço original antes do desconto, ou null>,
  "coupon_code": "<código do cupom, ou null>",
  "offer_url": "<URL que leva à oferta ou null>",
  "category_slug": "<uma das categorias permitidas>"
}}

Categorias permitidas: {categories}

Texto:
---
{text}
---
"""


def _record_usage(payload: dict, success: bool, operation: str = "offer_formatter") -> None:
    usage = payload.get("usage") or {}
    # OpenAI usa prompt/completion; Abacus RouteLLM usa input/output.
    prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    completion_tokens = int(
        usage.get("completion_tokens") or usage.get("output_tokens") or 0
    )
    total_tokens = int(usage.get("total_tokens") or prompt_tokens + completion_tokens)
    cost = (
        prompt_tokens * LLM_INPUT_COST_PER_MILLION
        + completion_tokens * LLM_OUTPUT_COST_PER_MILLION
    ) / 1_000_000
    try:
        with get_session() as session:
            session.add(
                LlmUsageEvent(
                    model=payload.get("model") or LLM_MODEL,
                    operation=operation,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost_usd=cost,
                    success=success,
                )
            )
            session.commit()
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao registrar consumo do LLM")


def _parse_json(content: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    return json.loads(cleaned)


def parse_llm(text: str) -> ParsedOffer:
    if not LLM_ENABLED:
        return ParsedOffer()

    payload: dict | None = None
    try:
        response = httpx.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={
                "Authorization": "Bearer " + LLM_API_KEY,
                # O WAF do RouteLLM rejeita o User-Agent padrão do httpx.
                "User-Agent": "curl/8.0",
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": _PROMPT.format(
                            text=text,
                            categories=", ".join(ALLOWED_CATEGORIES),
                        ),
                    }
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        data = _parse_json(payload["choices"][0]["message"]["content"])
        _record_usage(payload, success=True)
    except Exception:  # noqa: BLE001
        if payload is not None:
            _record_usage(payload, success=False)
        response_body = response.text[:500] if "response" in locals() else ""
        logger.exception("Falha ao chamar o Offer Formatter: %s", response_body)
        return ParsedOffer()

    return ParsedOffer(
        is_offer=bool(data.get("is_offer")),
        rejection_reason=data.get("rejection_reason"),
        product_name=data.get("product_name"),
        price=cents_to_amount(parse_brl_to_cents(data.get("price"))),
        price_original=cents_to_amount(parse_brl_to_cents(data.get("price_original"))),
        coupon_code=data.get("coupon_code"),
        category_slug=(
            data.get("category_slug")
            if data.get("category_slug") in ALLOWED_CATEGORIES
            else "outros"
        ),
        links=[data["offer_url"]] if data.get("offer_url") else [],
        confidence=0.9 if data.get("is_offer") else 1.0,
    )
