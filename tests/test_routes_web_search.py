"""Testes da lógica de busca/filtro do portal web (app/routes_web.py)."""
from datetime import datetime

from app.models import Offer
from app.offers_query import matches_query, normalize


def _offer(product_name="", raw_text=""):
    return Offer(
        source_platform="telegram",
        source_group="123",
        source_message_id="1",
        product_name=product_name,
        raw_text=raw_text,
        posted_at=datetime.utcnow(),
    )


def test_normalize_strips_accents_and_lowercases():
    assert normalize("Geladeira Frost-Free") == "geladeira frost-free"
    assert normalize("PROMOÇÃO relâmpago") == "promocao relampago"


def test_matches_query_is_word_order_independent():
    offer = _offer(product_name="RTX 5060 Ti 16GB Gigabyte")
    # Termos em ordem diferente da que aparecem no texto ainda devem bater.
    assert matches_query(offer, ["16gb", "rtx", "5060"])


def test_matches_query_is_accent_insensitive():
    offer = _offer(product_name="Placa de Vídeo GeForce RTX 5070")
    assert matches_query(offer, ["placa", "video"])


def test_matches_query_requires_all_terms():
    offer = _offer(product_name="Notebook Dell Inspiron")
    assert not matches_query(offer, ["notebook", "lenovo"])
    assert matches_query(offer, ["notebook", "dell"])


def test_matches_query_does_not_search_private_raw_text():
    offer = _offer(
        product_name="Gabinete Gamer Aquário Mancer CV700L",
        raw_text="Compatível com placa de vídeo de até 400 mm",
    )
    assert not matches_query(offer, ["placa", "video"])
