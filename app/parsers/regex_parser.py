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

# Número de preço em formato BR: milhar separado por ponto (opcional, em
# grupos de 3 dígitos) + centavos separados por vírgula (opcional). Cobre
# "74", "1.234", "1.234,56", "2.999" (sem centavos) e "11.699,10". Usar
# sempre este padrão (em vez de `[\d.]+,\d{2}|\d+` isolado) evita truncar
# valores tipo "R$2.999" no primeiro dígito antes do ponto (bug real: preço
# de R$2.999 virando R$2).
_PRICE_NUM = r"\d+(?:\.\d{3})*(?:,\d{2})?"
_PRICE_RE = re.compile(r"R\$\s*(" + _PRICE_NUM + r")")
_VALOR_LABEL_RE = re.compile(r"(?:valor|pre[cç]o)\s*:?\s*R\$\s*(" + _PRICE_NUM + r")", re.IGNORECASE)
# 💸/💰 são usados como rótulo de preço final em vários posts (ex: Shopee/
# AliExpress: "💸: R$2.999 no pix", "💸 R$ 3.219,00 (À Vista)",
# "💰 R$ 467") — mesma prioridade de "valor:".
_EMOJI_VALOR_RE = re.compile(r"[💸💰]\s*:?\s*R\$\s*(" + _PRICE_NUM + r")")
# "de"/"por" são preposições comuns em português — sem ancorar no início da
# linha, uma frase como "aplica o cupom de R$500 off" (desconto do cupom,
# não o preço do produto) batia com _DE_RE e virava o preço final errado
# (bug real observado: ofertas de R$2.999/R$3.219/etc. exibindo R$500).
# Só considera "de"/"por" como rótulo de preço quando abre a linha (com no
# máximo alguns caracteres não-alfanuméricos antes, tipo emoji/pontuação).
_LINE_START_PREFIX = r"^[^\w\n]{0,4}"
_DE_RE = re.compile(_LINE_START_PREFIX + r"de\s*:?\s*R\$\s*(" + _PRICE_NUM + r")", re.IGNORECASE | re.MULTILINE)
_POR_RE = re.compile(_LINE_START_PREFIX + r"por\s*:?\s*R\$\s*(" + _PRICE_NUM + r")", re.IGNORECASE | re.MULTILINE)
_CUPOM_RE = re.compile(r"cupom(?:\s+de\s+loja)?\s*:?\s*\+?\s*([A-Z0-9]{4,})", re.IGNORECASE)
# Usado só pelo fallback genérico (último recurso): remove menções a "cupom"
# antes de procurar um "R$ X" solto, pra não confundir o valor de desconto
# do cupom com o preço do produto.
_CUPOM_MENTION_RE = re.compile(r"cupom[^\n]*", re.IGNORECASE)
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
    emoji_valor_match = _EMOJI_VALOR_RE.search(text)
    por_match = _POR_RE.search(text)
    de_match = _DE_RE.search(text)

    if valor_match:
        price = _to_float(valor_match.group(1))
    elif emoji_valor_match:
        price = _to_float(emoji_valor_match.group(1))
    elif por_match:
        price = _to_float(por_match.group(1))
        if de_match:
            price_original = _to_float(de_match.group(1))
    elif de_match:
        # só achou "De:" sem "Por:" — trata como preço único
        price = _to_float(de_match.group(1))
    else:
        # último recurso: primeiro "R$ X" solto no texto, mas ignorando
        # menções a "cupom" (ex: "cupom de R$500 off"), que são valor de
        # desconto e não o preço do produto.
        generic_match = _PRICE_RE.search(_CUPOM_MENTION_RE.sub("", text))
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
