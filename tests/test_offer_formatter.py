from app.parsers.pipeline import extract


def test_prefilter_rejects_non_offer_without_url():
    result, method = extract("Bom dia! Alguém sabe se a loja abre hoje?")
    assert method == "prefilter-rejected"
    assert result.is_offer is False


def test_local_fallback_accepts_complete_offer_when_llm_disabled():
    result, method = extract(
        "Notebook Lenovo IdeaPad\nValor: R$ 2.999,00\n"
        "Link: https://example.com/notebook"
    )
    assert method == "regex"
    assert result.is_offer is True
    assert result.product_name == "Notebook Lenovo IdeaPad"
    assert result.price == 2999.0
