from decimal import Decimal

from ids.domain.value_objects import Price

NBSP = "\u00a0"
MINUS = "\u2212"
MIN_DECIMALS = 2


def format_pln(value: Decimal) -> str:
    sign = MINUS if value < 0 else ""
    abs_str = f"{abs(value):,.2f}".replace(",", NBSP)
    return f"{sign}{abs_str} PLN"


def format_pln_signed(value: Decimal) -> str:
    if value >= 0:
        return f"+{format_pln(value)}"
    return format_pln(value)


def format_pct_unsigned(value: Decimal) -> str:
    return f"{value:.2f} %"


def format_pct_signed(value: Decimal) -> str:
    if value >= 0:
        return f"+{value:.2f}%"
    return f"{MINUS}{abs(value):.2f}%"


def format_price(value: Price | Decimal) -> str:
    amount = value.value if isinstance(value, Price) else value
    integer, fraction = f"{amount:.4f}".split(".")
    trimmed = fraction.rstrip("0")
    if len(trimmed) < MIN_DECIMALS:
        trimmed = trimmed.ljust(MIN_DECIMALS, "0")
    return f"{integer}.{trimmed}"
