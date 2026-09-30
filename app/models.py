"""Modelos de dados (SQLModel) do descont.io."""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Offer(SQLModel, table=True):
    __tablename__ = "offers"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Origem (chave de deduplicação: mesma plataforma+grupo+message_id nunca duplica)
    source_platform: str = Field(index=True)  # "telegram" | "whatsapp"
    source_group: str = Field(index=True)  # chat_id/JID bruto
    source_label: str = ""  # nome de exibição do grupo/canal
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
    category: Optional[str] = None

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
