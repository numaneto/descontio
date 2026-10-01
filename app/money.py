"""Conversão e formatação de valores monetários em BRL."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

BRL_SCALE = Decimal("0.01")
MAX_PRICE_CENTS = 100_000_000


def amount_to_cents(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        amount = Decimal(str(value)).quantize(BRL_SCALE, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None
    cents = int(amount * 100)
    if 0 <= cents <= MAX_PRICE_CENTS:
        return cents
    return None


def parse_brl_to_cents(value: str | int | float | None) -> int | None:
    """Aceita 5060.00, 5060,00 ou 5.060,00 e devolve centavos."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return amount_to_cents(value)

    raw = str(value).strip().replace("R$", "").replace(" ", "")
    if not raw:
        return None

    if "," in raw:
        normalized = raw.replace(".", "").replace(",", ".")
    elif raw.count(".") > 1 or (raw.count(".") == 1 and len(raw.rsplit(".", 1)[1]) == 3):
        normalized = raw.replace(".", "")
    else:
        normalized = raw
    return amount_to_cents(normalized)


def cents_to_amount(cents: int | None) -> float | None:
    return None if cents is None else cents / 100


def format_brl(cents: int | None) -> str:
    if cents is None:
        return ""
    amount = Decimal(cents) / 100
    formatted = f"{amount:,.2f}"
    return "R$ " + formatted.replace(",", "_").replace(".", ",").replace("_", ".")
