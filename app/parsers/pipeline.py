"""Pipeline híbrido: regex primeiro (sem custo, cobre a maioria dos posts
já bem formatados), LLM só como fallback pra texto livre sem rótulos
reconhecíveis."""
import re

from app.parsers.llm_parser import parse_llm
from app.parsers.regex_parser import ParsedOffer, parse_regex

_URL_RE = re.compile(r"https?://\S+")

# Abaixo desse valor de confiança do regex, tenta o fallback de LLM.
_MIN_CONFIDENCE = 0.5


def extract(text: str) -> tuple[ParsedOffer, str]:
    """Retorna (ParsedOffer, metodo) onde metodo é 'regex', 'llm' ou 'unmatched'."""
    regex_result = parse_regex(text)

    if regex_result.confidence >= _MIN_CONFIDENCE:
        return regex_result, "regex"

    llm_result = parse_llm(text)
    if llm_result.confidence > 0:
        # Preserva links extraídos por regex (o LLM não é confiável pra isso)
        llm_result.links = llm_result.links or _URL_RE.findall(text)
        return llm_result, "llm"

    # Nenhum dos dois conseguiu — devolve o melhor que o regex achou mesmo
    # assim (pode ter só links, por exemplo), marcado como não-confiável.
    return regex_result, "unmatched"
