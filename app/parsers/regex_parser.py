"""Extração por regex de produto/preço/cupom/links a partir do texto bruto
de um post, cobrindo os formatos observados nos grupos de ofertas:

  1) Rótulos explícitos (mais comum):
     🔥Nome do produto🔥
     🐾 Valor: R$ 74
     🏷️ Cupom: F1MD0D1A
     🔗 Link: https://...
     #Anuncio

  2) Preço "de/por" (comum em posts de afiliado tipo AliExpress):
     Nome do produto
     De: R$125,19
     Por: R$71,69
     Link ...: https://...

Qualquer formato novo pode ser coberto adicionando um padrão aqui — o
fallback via LLM (`llm_parser.py`) só é acionado quando nada abaixo bate.
"""
import re
from dataclasses import dataclass, field

_PRICE_RE = re.compile(r"R\$\s*([\d.]+,\d{2}|\d+)")
_VALOR_LABEL_RE = re.compile(r"(?:valor|pre[cç]o)\s*:?\s*R\$\s*([\d.]+,\d{2}|\d+)", re.IGNORECASE)
_DE_RE = re.compile(r"\bde\s*:?\s*R\$\s*([\d.]+,\d{2}|\d+)", re.IGNORECASE)
_POR_RE = re.compile(r"\bpor\s*:?\s*R\$\s*([\d.]+,\d{2}|\d+)", re.IGNORECASE)
_CUPOM_RE = re.compile(r"cupom(?:\s+de\s+loja)?\s*:?\s*\+?\s*([A-Z0-9]{4,})", re.IGNORECASE)
_URL_RE = re.compile(r"https?://\S+")
_HASHTAG_OR_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]|#\w+", re.UNICODE
)


@dataclass
class ParsedOffer:
    product_name: str | None = None
    price: float | None = None
    price_original: float | None = None
    coupon_code: str | None = None
    links: list[str] = field(default_factory=list)
    confidence: float = 0.0


def _to_float(raw: str) -> float:
    """Converte 'R$ 1.234,56' / 'R$ 74' pro float 1234.56 / 74.0."""
    cleaned = raw.replace(".", "").replace(",", ".")
    return float(cleaned)


def _guess_product_name(text: str) -> str | None:
    for line in text.splitlines():
        stripped = _HASHTAG_OR_EMOJI_RE.sub("", line).strip(" 🔥*_-")
        if stripped and not stripped.lower().startswith(("valor", "cupom", "link", "de:", "por:")):
            return stripped
    return None


def parse_regex(text: str) -> ParsedOffer:
    if not text:
        return ParsedOffer()

    links = _URL_RE.findall(text)
    coupon_match = _CUPOM_RE.search(text)
    coupon_code = coupon_match.group(1) if coupon_match else None

    price: float | None = None
    price_original: float | None = None

    valor_match = _VALOR_LABEL_RE.search(text)
    por_match = _POR_RE.search(text)
    de_match = _DE_RE.search(text)

    if valor_match:
        price = _to_float(valor_match.group(1))
    elif por_match:
        price = _to_float(por_match.group(1))
        if de_match:
            price_original = _to_float(de_match.group(1))
    elif de_match:
        # só achou "De:" sem "Por:" — trata como preço único
        price = _to_float(de_match.group(1))
    else:
        # último recurso: primeiro "R$ X" solto no texto
        generic_match = _PRICE_RE.search(text)
        if generic_match:
            price = _to_float(generic_match.group(1))

    product_name = _guess_product_name(text)

    # Confiança: precisa de preço + nome de produto pra ser considerado
    # "resolvido" só por regex; caso contrário o pipeline decide se manda
    # pro fallback de LLM.
    confidence = 0.0
    if price is not None:
        confidence += 0.5
    if product_name:
        confidence += 0.3
    if links:
        confidence += 0.2

    return ParsedOffer(
        product_name=product_name,
        price=price,
        price_original=price_original,
        coupon_code=coupon_code,
        links=links,
        confidence=round(confidence, 2),
    )
