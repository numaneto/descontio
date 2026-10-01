from app.money import amount_to_cents, format_brl, parse_brl_to_cents


def test_parse_brl_formats_to_integer_cents():
    assert parse_brl_to_cents("5.060,00") == 506000
    assert parse_brl_to_cents("5060,00") == 506000
    assert parse_brl_to_cents("5060.00") == 506000
    assert parse_brl_to_cents("R$ 2.999") == 299900


def test_amount_to_cents_uses_decimal_rounding():
    assert amount_to_cents(71.69) == 7169
    assert amount_to_cents("0.105") == 11


def test_format_brl():
    assert format_brl(506000) == "R$ 5.060,00"
    assert format_brl(5) == "R$ 0,05"
