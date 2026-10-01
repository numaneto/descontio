from app.categories import classify_category_slug, classify_subcategory_slug


def test_classifies_common_offer_categories_without_llm():
    assert classify_category_slug("Placa de Vídeo GeForce RTX 5070") == "informatica"
    assert classify_category_slug("Gabinete Gamer Aquário Mancer") == "informatica"
    assert classify_category_slug("Smartphone Samsung Galaxy S25") == "celulares"
    assert classify_category_slug("Geladeira Frost Free 480L") == "eletrodomesticos"
    assert classify_category_slug("Fone Bluetooth JBL") == "eletronicos"
    assert classify_category_slug("Panela de Pressão Tramontina") == "casa-cozinha"


def test_unknown_product_goes_to_others():
    assert classify_category_slug("Produto promocional edição especial") == "outros"


def test_classifies_informatica_subcategories():
    assert (
        classify_subcategory_slug("Placa de Vídeo GeForce RTX 5070", "informatica")
        == "placas-de-video"
    )
    assert (
        classify_subcategory_slug("Notebook Dell Inspiron i7", "informatica")
        == "notebooks"
    )
    assert (
        classify_subcategory_slug("Gabinete Gamer Aquário Mancer", "informatica")
        == "componentes"
    )


def test_subcategory_is_none_when_no_keyword_matches():
    assert classify_subcategory_slug("Produto genérico de informática", "informatica") is None


def test_subcategory_is_none_for_category_without_taxonomy():
    assert classify_subcategory_slug("Qualquer coisa", "outros") is None
