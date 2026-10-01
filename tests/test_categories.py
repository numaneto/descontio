from app.categories import classify_category_slug


def test_classifies_common_offer_categories_without_llm():
    assert classify_category_slug("Placa de Vídeo GeForce RTX 5070") == "informatica"
    assert classify_category_slug("Gabinete Gamer Aquário Mancer") == "informatica"
    assert classify_category_slug("Smartphone Samsung Galaxy S25") == "celulares"
    assert classify_category_slug("Geladeira Frost Free 480L") == "eletrodomesticos"
    assert classify_category_slug("Fone Bluetooth JBL") == "eletronicos"
    assert classify_category_slug("Panela de Pressão Tramontina") == "casa-cozinha"


def test_unknown_product_goes_to_others():
    assert classify_category_slug("Produto promocional edição especial") == "outros"
