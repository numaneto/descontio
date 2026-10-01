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


# Subcategorias por categoria-pai — mesma lógica de palavras-chave do nível
# acima, só que restrita a um subconjunto de produtos dentro da categoria.
# Nem toda categoria tem subcategoria (ex.: "outros" nunca tem, "viagens-servicos"
# tem poucas) — categorias sem entrada aqui simplesmente não oferecem o filtro
# mais granular, o que é esperado, não um bug.
SUBCATEGORY_KEYWORDS: dict[str, tuple[tuple[str, str, tuple[str, ...]], ...]] = {
    "informatica": (
        (
            "Placas de vídeo", "placas-de-video",
            ("placa de video", "geforce", "radeon rx", "rtx ", "gtx "),
        ),
        (
            "Notebooks", "notebooks",
            ("notebook", "laptop", "ultrabook"),
        ),
        (
            "Componentes", "componentes",
            (
                "placa mae", "processador", "memoria ram", "fonte atx",
                "cooler", "gabinete",
            ),
        ),
        (
            "Armazenamento e redes", "armazenamento-redes",
            ("ssd", "hd externo", "pendrive", "roteador", "wi-fi", "wifi"),
        ),
        (
            "Periféricos", "perifericos",
            ("monitor", "teclado", "mouse", "webcam", "impressora"),
        ),
    ),
    "celulares": (
        (
            "Smartphones", "smartphones",
            (
                "smartphone", "celular", "iphone", "galaxy", "redmi",
                "poco ", "motorola", "xiaomi",
            ),
        ),
        (
            "Tablets", "tablets",
            ("tablet", "ipad"),
        ),
        (
            "Acessórios para celular", "acessorios-celular",
            ("capinha",),
        ),
    ),
    "games": (
        (
            "Consoles", "consoles",
            ("playstation", "ps4", "ps5", "xbox", "nintendo", "switch", "console"),
        ),
        (
            "Controles e acessórios", "controles-acessorios",
            ("controle gamer",),
        ),
        (
            "Jogos", "jogos",
            ("jogo para",),
        ),
    ),
    "eletronicos": (
        (
            "TV e imagem", "tv-imagem",
            ("smart tv", "televisao", " tv ", "projetor"),
        ),
        (
            "Áudio", "audio",
            ("fone", "headset", "caixa de som", "soundbar"),
        ),
        (
            "Wearables", "wearables",
            ("smartwatch", "relogio inteligente"),
        ),
        (
            "Câmeras e drones", "cameras-drones",
            ("camera", "drone"),
        ),
        (
            "Energia e cabos", "energia-cabos",
            ("carregador", "power bank", "bateria", "pilha"),
        ),
    ),
    "eletrodomesticos": (
        (
            "Cozinha", "cozinha-eletro",
            (
                "geladeira", "refrigerador", "fogao", "micro-ondas",
                "microondas", "air fryer", "fritadeira", "liquidificador",
                "cafeteira", "batedeira", "freezer",
            ),
        ),
        (
            "Lavanderia e limpeza", "lavanderia-limpeza",
            ("aspirador", "lava-loucas", "lavadora", "secadora"),
        ),
        (
            "Climatização", "climatizacao",
            ("ar-condicionado", "ventilador", "purificador"),
        ),
    ),
    "moda-beleza": (
        (
            "Calçados", "calcados",
            ("tenis", "sapato", "sandalia", "chinelo"),
        ),
        (
            "Vestuário", "vestuario",
            ("camisa", "camiseta", "calca", "vestido", "jaqueta"),
        ),
        (
            "Beleza e cuidados", "beleza-cuidados",
            (
                "perfume", "maquiagem", "batom", "shampoo", "condicionador",
                "hidratante", "protetor solar",
            ),
        ),
    ),
    "mercado": (
        (
            "Bebidas", "bebidas",
            ("cerveja", "vinho", "whisky", "refrigerante"),
        ),
        (
            "Alimentos", "alimentos",
            (
                "cafe ", "cafe em", "chocolate", "biscoito", "leite ",
                "arroz", "feijao", "azeite",
            ),
        ),
        (
            "Limpeza e higiene", "limpeza-higiene",
            ("detergente", "sabao", "fralda", "papel higienico"),
        ),
    ),
    "esporte-lazer": (
        (
            "Fitness", "fitness",
            ("bicicleta", "esteira", "halter", "academia"),
        ),
        (
            "Camping e aventura", "camping-aventura",
            (
                "camping", "barraca", "pesca", "vara de pescar",
                "mochila de trilha", "prancha",
            ),
        ),
        (
            "Esportes com bola e rodas", "esportes-bola-rodas",
            ("bola ", "chuteira", "patins", "skate"),
        ),
    ),
    "ferramentas-automotivo": (
        (
            "Ferramentas", "ferramentas",
            (
                "furadeira", "parafusadeira", "serra ", "martelete",
                "compressor", "ferramenta",
            ),
        ),
        (
            "Automotivo", "automotivo",
            (
                "pneu", "oleo motor", "automotivo", "carro", "moto ",
                "lavadora de alta pressao",
            ),
        ),
        (
            "Proteção", "protecao-automotiva",
            ("capacete",),
        ),
    ),
    "viagens-servicos": (
        (
            "Passagens e hospedagem", "passagens-hospedagem",
            ("passagem", "hotel", "hospedagem", "viagem"),
        ),
        (
            "Assinaturas e seguros", "assinaturas-seguros",
            ("assinatura", "streaming", "plano de internet", "seguro"),
        ),
    ),
    "casa-cozinha": (
        (
            "Cozinha", "cozinha-utensilios",
            ("panela", "frigideira", "talher"),
        ),
        (
            "Cama, mesa e banho", "cama-mesa-banho",
            ("jogo de cama", "toalha", "colchao", "travesseiro"),
        ),
        (
            "Móveis", "moveis",
            ("sofa", "mesa", "cadeira", "armario", "estante"),
        ),
        (
            "Iluminação e hidráulica", "iluminacao-hidraulica",
            ("luminaria", "lampada", "torneira", "chuveiro"),
        ),
    ),
}


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


def classify_subcategory_slug(product_name: str | None, category_slug: str) -> str | None:
    """Tenta achar uma subcategoria dentro de `category_slug`. Devolve
    `None` quando a categoria não tem subcategorias cadastradas ou nenhuma
    palavra-chave bate — nesse caso a oferta fica só no nível pai, o que é
    o comportamento esperado (nem todo produto precisa de uma subcategoria)."""
    normalized = f" {_normalize(product_name or '')} "
    for _name, slug, keywords in SUBCATEGORY_KEYWORDS.get(category_slug, ()):
        if any(keyword in normalized for keyword in keywords):
            return slug
    return None
