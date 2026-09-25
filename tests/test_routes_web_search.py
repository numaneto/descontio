"""Testes da lógica de busca/filtro do portal web (app/routes_web.py)."""
from datetime import datetime

from app.models import Offer
from app.routes_web import _matches_query, _normalize


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
    assert _normalize("Geladeira Frost-Free") == "geladeira frost-free"
    assert _normalize("PROMOÇÃO relâmpago") == "promocao relampago"


def test_matches_query_is_word_order_independent():
    offer = _offer(product_name="RTX 5060 Ti 16GB Gigabyte")
    # Termos em ordem diferente da que aparecem no texto ainda devem bater.
    assert _matches_query(offer, ["16gb", "rtx", "5060"])


def test_matches_query_is_accent_insensitive():
    offer = _offer(product_name="Geladeira Panasonic Frost Free", raw_text="promoção relâmpago")
    assert _matches_query(offer, ["promocao", "relampago"])


def test_matches_query_requires_all_terms():
    offer = _offer(product_name="Notebook Dell Inspiron")
    assert not _matches_query(offer, ["notebook", "lenovo"])
    assert _matches_query(offer, ["notebook", "dell"])


def test_matches_query_searches_raw_text_too():
    offer = _offer(product_name=None, raw_text="Fone de ouvido JBL Tune 510BT por R$149")
    assert _matches_query(offer, ["jbl", "510bt"])
