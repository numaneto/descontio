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


# Bug real (produção, 2026-09-25): posts que mencionam "cupom de R$X off"
# no corpo do texto tinham esse valor de desconto extraído como se fosse o
# preço final do produto, porque "de"/"por" não eram ancorados ao início da
# linha. Ex.: oferta de R$2.999 aparecendo como R$500 no portal.
CUPOM_MENTION_EXAMPLE = """💥🙀 Placa de Vídeo PowerColor Reaper AMD Radeon RX 9060 XT 16GB

💸: R$2.999 no pix + frete grátis!
👉: https://s.shopee.com.br/30oFKTiNYL

Na hora de finalizar aplica o cupom de R$500 off apenas no app!
https://s.shopee.com.br/4ftAtRreEQ

#anuncio"""

BENCHPROMOS_CUPOM_EXAMPLE = """🔥 Notebook Lenovo IdeaPad Slim 3 AMD Ryzen 7 7735HS 8GB 512GB SSD 15.3" WUXGA Linux - R$ 3.219,00 🔥 #anúncio

🎟 Cupom: Cupom de R$ 500 OFF no carrinho
💸 R$ 3.219,00 (À Vista)

🔗 https://benchpromos.com/promocao/exemplo"""


def test_parse_regex_ignores_cupom_discount_as_price():
    result = parse_regex(CUPOM_MENTION_EXAMPLE)
    assert result.price == 2999.0


def test_parse_regex_benchpromos_ignores_cupom_discount():
    result = parse_regex(BENCHPROMOS_CUPOM_EXAMPLE)
    assert result.price == 3219.0


def test_parse_regex_thousand_separator_without_cents():
    # "R$2.999" (sem centavos) não pode truncar pro primeiro dígito antes
    # do ponto (bug real: virava R$2).
    result = parse_regex("💰 R$ 2.835 PIX")
    assert result.price == 2835.0
