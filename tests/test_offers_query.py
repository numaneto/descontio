from datetime import datetime

from sqlmodel import Session, SQLModel, create_engine

from app.models import Category, Offer
from app.offers_query import query_offers


def _offer(name: str, cents: int, category_id: int, raw_text: str = "") -> Offer:
    return Offer(
        source_platform="telegram",
        source_group="123",
        source_message_id=name,
        product_name=name,
        raw_text=raw_text,
        price=cents / 100,
        price_cents=cents,
        category_id=category_id,
        posted_at=datetime.utcnow(),
    )


def test_query_filters_integer_cents_category_and_normalized_name():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        hardware = Category(name="Informática e hardware", slug="informatica")
        casa = Category(name="Casa e cozinha", slug="casa-cozinha")
        session.add(hardware)
        session.add(casa)
        session.commit()
        session.refresh(hardware)
        session.refresh(casa)
        session.add(
            _offer(
                "Placa de Vídeo GeForce RTX 5070",
                506000,
                hardware.id,
            )
        )
        session.add(
            _offer(
                "Gabinete Gamer Aquário",
                22400,
                hardware.id,
                raw_text="Compatível com placa de vídeo grande",
            )
        )
        session.add(_offer("Panela elétrica", 29990, casa.id))
        session.commit()

        results = query_offers(
            session,
            q="placa de video",
            category_slug="informatica",
            price_min_cents=506000,
            price_max_cents=506000,
        )

    assert [offer.product_name for offer in results] == [
        "Placa de Vídeo GeForce RTX 5070"
    ]
