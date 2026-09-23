"""Testes do parser por regex, usando exemplos reais de posts de grupos de
promoções (formatos coletados diretamente dos canais monitorados)."""
from app.parsers.regex_parser import parse_regex

FIRE_EXAMPLE = """🔥Kit Ventoinhas Pichau Ventus Nx, Argb, 3x120mm, Preto, Pch-Vtnx3-Bk01🔥

🐾 Valor: R$ 74

🏷️ Cupom: F1MD0D1A

🔗 Link: https://seuhardware.com/s/OqH010M

#Anuncio"""

DE_POR_EXAMPLE = """Fone GK Kunten Pro

Lançamento!

De: R$125,19

Por: R$71,69

Cupom de loja + 670 moedas

Link com moedas 👇
https://s.click.aliexpress.com/e/_c4kUOGrn

Link direto 👇
https://s.click.aliexpress.com/e/_c3hlalpn"""


def test_parse_regex_labeled_format():
    result = parse_regex(FIRE_EXAMPLE)
    assert result.product_name == "Kit Ventoinhas Pichau Ventus Nx, Argb, 3x120mm, Preto, Pch-Vtnx3-Bk01"
    assert result.price == 74.0
    assert result.coupon_code == "F1MD0D1A"
    assert result.links == ["https://seuhardware.com/s/OqH010M"]
    assert result.confidence >= 0.5


def test_parse_regex_de_por_format():
    result = parse_regex(DE_POR_EXAMPLE)
    assert result.product_name == "Fone GK Kunten Pro"
    assert result.price == 71.69
    assert result.price_original == 125.19
    assert len(result.links) == 2
    assert result.confidence >= 0.5


def test_parse_regex_empty_text():
    result = parse_regex("")
    assert result.price is None
    assert result.confidence == 0.0


def test_parse_regex_unstructured_text_low_confidence():
    result = parse_regex("Oi pessoal, bom dia! Alguém viu o preço do dólar hoje?")
    assert result.price is None
    assert result.confidence < 0.5
