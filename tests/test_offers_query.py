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


def test_query_by_parent_category_includes_subcategory_offers():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        hardware = Category(name="Informática e hardware", slug="informatica")
        session.add(hardware)
        session.commit()
        session.refresh(hardware)
        gpus = Category(name="Placas de vídeo", slug="placas-de-video", parent_id=hardware.id)
        session.add(gpus)
        session.commit()
        session.refresh(gpus)

        session.add(_offer("RTX 5070", 500000, gpus.id))
        session.add(_offer("Gabinete Gamer", 20000, hardware.id))
        session.commit()

        by_parent = query_offers(session, category_slug="informatica")
        by_subcategory = query_offers(session, category_slug="placas-de-video")

    assert {offer.product_name for offer in by_parent} == {"RTX 5070", "Gabinete Gamer"}
    assert [offer.product_name for offer in by_subcategory] == ["RTX 5070"]


def test_query_sorts_by_price_asc_and_desc_with_nulls_last():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        hardware = Category(name="Informática e hardware", slug="informatica")
        session.add(hardware)
        session.commit()
        session.refresh(hardware)

        session.add(_offer("Barato", 10000, hardware.id))
        session.add(_offer("Caro", 90000, hardware.id))
        no_price = _offer("Sem preco", 0, hardware.id)
        no_price.price_cents = None
        session.add(no_price)
        session.commit()

        asc = query_offers(session, category_slug="informatica", sort="price_asc")
        desc = query_offers(session, category_slug="informatica", sort="price_desc")

    assert [offer.product_name for offer in asc] == ["Barato", "Caro", "Sem preco"]
    assert [offer.product_name for offer in desc] == ["Caro", "Barato", "Sem preco"]
