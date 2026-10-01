"""Offer Formatter: pré-filtro barato e normalização agnóstica via LLM."""
import re

from app.config import LLM_ENABLED
from app.parsers.llm_parser import parse_llm
from app.parsers.regex_parser import ParsedOffer, parse_regex

_URL_RE = re.compile(r"https?://\S+")
_COMMERCIAL_SIGNAL_RE = re.compile(
    r"R\$|pre[cç]o|valor|cupom|desconto|oferta|promo[cç][aã]o|por apenas|pix",
    re.IGNORECASE,
)


def extract(text: str) -> tuple[ParsedOffer, str]:
    """Retorna (ParsedOffer, método), rejeitando ruído antes de gastar tokens."""
    regex_result = parse_regex(text)

    if not _URL_RE.search(text) or not _COMMERCIAL_SIGNAL_RE.search(text):
        regex_result.is_offer = False
        regex_result.rejection_reason = "sem URL ou sinal comercial"
        return regex_result, "prefilter-rejected"

    if LLM_ENABLED:
        llm_result = parse_llm(text)
        if llm_result.is_offer is not None:
            llm_result.links = llm_result.links or _URL_RE.findall(text)
            return llm_result, "llm"

    if regex_result.is_offer:
        return regex_result, "regex"

    regex_result.is_offer = False
    regex_result.rejection_reason = "dados insuficientes para formar uma oferta"
    return regex_result, "unmatched"
