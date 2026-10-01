"""Modelos de dados (SQLModel) do descont.io."""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Offer(SQLModel, table=True):
    __tablename__ = "offers"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Origem (chave de deduplicação: mesma plataforma+grupo+message_id nunca duplica)
    source_platform: str = Field(index=True)  # "telegram" | "email" | "crawler" | "api"
    source_group: str = Field(index=True)  # identificador interno da origem
    source_label: str = ""  # rótulo interno; nunca deve ser exposto ao público
    source_message_id: str = Field(index=True)

    # Conteúdo bruto
    raw_text: str = ""
    image_path: Optional[str] = None

    # Campos normalizados (podem ser None se o parser não conseguiu extrair)
    product_name: Optional[str] = None
    price: Optional[float] = None
    price_original: Optional[float] = None
    coupon_code: Optional[str] = None
    links: str = "[]"  # JSON-encoded list[str]
    category: Optional[str] = None  # legado: string livre, mantido por compatibilidade

    # Classificação estruturada (Classe/Subclasse) — nullable de propósito:
    # ofertas existentes ficam sem classificação até um processo futuro
    # (manual ou LLM) preencher; nenhuma oferta é bloqueada por falta disso.
    category_id: Optional[int] = Field(default=None, foreign_key="categories.id", index=True)
    product_id: Optional[int] = Field(default=None, foreign_key="products.id", index=True)

    # Metadados de parsing/engajamento
    parse_method: str = "unmatched"  # "regex" | "llm" | "unmatched"
    parse_confidence: float = 0.0
    engagement_score: int = 0  # reações + encaminhamentos, se disponível

    # Retenção: quando True, a imagem física já foi apagada do disco (ver
    # scripts/retention_cleanup.py) e a oferta some da busca padrão do
    # portal — o texto/metadados continuam no banco (não é hard-delete).
    archived: bool = Field(default=False, index=True)

    posted_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    ingested_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        # (source_platform, source_group, source_message_id) deve ser único —
        # aplicado via índice composto na migração (scripts/init_db.py).
        pass


class ChannelPollState(SQLModel, table=True):
    """Estado de polling por canal — substitui a conexão viva do worker
    antigo (client.on(events.NewMessage())) por ciclos curtos e
    independentes: cada execução de scripts/poll_telegram.py busca só
    mensagens com id > last_message_id (via iter_messages(min_id=...)),
    evita rebaixar imagens de posts já vistos, e não depende de uma conexão
    que precisa ficar viva por dias sem falhar silenciosamente (ver
    incidente 2026-09-30 em STATUS.md: o listener parou de despachar
    NewMessage por 9h+ sem nenhum erro nos logs)."""

    __tablename__ = "channel_poll_state"

    platform: str = Field(primary_key=True)
    chat_id: str = Field(primary_key=True)
    last_message_id: int = Field(default=0)
    last_polled_at: Optional[datetime] = None


class Category(SQLModel, table=True):
    """Árvore de classificação (Classe/Subclasse/...), auto-referenciada
    via `parent_id` — ex.: "Hardware" (raiz) -> "GPUs" (filho) ->
    "NVIDIA"/"AMD" (futuro neto, quando fizer sentido detalhar por
    fabricante). Sem limite de profundidade fixo: cada nível só é criado
    quando a granularidade compensar (não adianta subclasse com 1 produto
    só)."""

    __tablename__ = "categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(index=True, unique=True)
    parent_id: Optional[int] = Field(default=None, foreign_key="categories.id", index=True)


class Product(SQLModel, table=True):
    """Entidade canônica de produto — várias `Offer` (posts brutos, um por
    anúncio/repostagem) podem apontar pro mesmo `Product` depois de
    classificadas/normalizadas. É o que permite, no futuro, responder
    "histórico de preço da GPU X" agregando várias ofertas diferentes em
    vez de tratar cada post como um item isolado."""

    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    category_id: Optional[int] = Field(default=None, foreign_key="categories.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Channel(SQLModel, table=True):
    """Canal/grupo monitorado — antes vivia só em config/channels.yaml
    (estático, exigia editar arquivo + redeploy pra mudar). Agora é a
    fonte de verdade em runtime pra permitir habilitar/desabilitar e
    ocultar a marca (nome do canal) na interface pública pela admin UI,
    sem precisar editar YAML nem reiniciar container. O YAML populado
    manualmente continua existindo só como seed inicial (ver
    scripts/seed_channels_from_yaml.py)."""

    __tablename__ = "channels"

    platform: str = Field(primary_key=True)
    chat_id: str = Field(primary_key=True)
    label: str
    category: Optional[str] = None
    enabled: bool = Field(default=True, index=True)
    # Quando True, a interface pública (portal + API) mostra um rótulo
    # genérico em vez do nome real do canal — a oferta continua visível,
    # só a marca/fonte fica oculta.
    hide_brand: bool = Field(default=False)


class ApiKey(SQLModel, table=True):
    """Chave de acesso da API pública — opcional: sem key, o consumidor cai
    no rate limit anônimo (bem baixo, ver app/rate_limit.py); com uma key
    válida, usa o `rate_limit_per_hour` configurado aqui (default bem mais
    alto). A chave em si NUNCA é armazenada em texto puro — só o hash
    SHA-256 (`key_hash`); o valor real só é mostrado uma vez, no momento da
    criação (ver app/routes_admin.py)."""

    __tablename__ = "api_keys"

    id: Optional[int] = Field(default=None, primary_key=True)
    key_hash: str = Field(index=True, unique=True)
    label: str  # identifica o dono/uso da key (ex.: "app do Fulano")
    rate_limit_per_hour: int = Field(default=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    revoked_at: Optional[datetime] = None
