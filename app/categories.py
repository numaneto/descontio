"""Taxonomia pública controlada e classificação local de categorias amplas."""
import unicodedata

CATEGORY_KEYWORDS = (
    (
        "celulares",
        (
            "smartphone", "celular", "iphone", "galaxy", "redmi", "poco ",
            "motorola", "xiaomi", "tablet", "ipad", "capinha",
        ),
    ),
    (
        "games",
        (
            "playstation", "ps4", "ps5", "xbox", "nintendo", "switch",
            "console", "controle gamer", "jogo para",
        ),
    ),
    (
        "eletrodomesticos",
        (
            "geladeira", "refrigerador", "fogao", "micro-ondas", "microondas",
            "air fryer", "fritadeira", "lava-loucas", "lavadora", "aspirador",
            "ar-condicionado", "ventilador", "liquidificador", "cafeteira",
            "batedeira", "purificador", "freezer", "secadora",
        ),
    ),
    (
        "moda-beleza",
        (
            "tenis", "sapato", "sandalia", "chinelo", "camisa", "camiseta",
            "calca", "vestido", "jaqueta", "perfume", "maquiagem", "batom",
            "shampoo", "condicionador", "hidratante", "protetor solar",
        ),
    ),
    (
        "mercado",
        (
            "cafe ", "cafe em", "chocolate", "cerveja", "vinho", "whisky",
            "refrigerante", "biscoito", "leite ", "arroz", "feijao", "azeite",
            "detergente", "sabao", "fralda", "papel higienico",
        ),
    ),
    (
        "esporte-lazer",
        (
            "bicicleta", "esteira", "halter", "academia", "camping", "barraca",
            "pesca", "vara de pescar", "bola ", "chuteira", "mochila de trilha",
            "prancha", "patins", "skate",
        ),
    ),
    (
        "ferramentas-automotivo",
        (
            "furadeira", "parafusadeira", "serra ", "martelete", "compressor",
            "ferramenta", "pneu", "oleo motor", "automotivo", "carro", "moto ",
            "capacete", "lavadora de alta pressao",
        ),
    ),
    (
        "viagens-servicos",
        (
            "passagem", "hotel", "hospedagem", "viagem", "assinatura",
            "streaming", "plano de internet", "seguro",
        ),
    ),
    (
        "informatica",
        (
            "notebook", "laptop", "computador", "desktop", "placa de video",
            "placa mae", "processador", "memoria ram", "ssd", "hd externo",
            "gabinete", "monitor", "teclado", "mouse", "webcam", "impressora",
            "roteador", "wi-fi", "wifi", "pendrive", "cooler", "fonte atx",
        ),
    ),
    (
        "eletronicos",
        (
            "smart tv", "televisao", " tv ", "fone", "headset", "caixa de som",
            "soundbar", "smartwatch", "relogio inteligente", "camera", "drone",
            "projetor", "carregador", "power bank", "bateria", "pilha",
        ),
    ),
    (
        "casa-cozinha",
        (
            "panela", "frigideira", "talher", "jogo de cama", "toalha",
            "colchao", "travesseiro", "sofa", "mesa", "cadeira", "armario",
            "estante", "luminaria", "lampada", "torneira", "chuveiro",
        ),
    ),
)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    ).lower()


def classify_category_slug(product_name: str | None) -> str:
    normalized = f" {_normalize(product_name or '')} "
    for slug, keywords in CATEGORY_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return slug
    return "outros"
