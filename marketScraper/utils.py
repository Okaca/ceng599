import re

# unit in a product name -> (unit stored in the db, multiplier to get there)
UNITS = {
    "kg": ("g", 1000),
    "gr": ("g", 1),
    "g": ("g", 1),
    "lt": ("ml", 1000),
    "l": ("ml", 1000),
    "cl": ("ml", 10),
    "ml": ("ml", 1),
    "adet": ("adet", 1),
    "ürün": ("adet", 1),  # Getir: "2 Ürün"
}

# sizes above this are typos on the site ("Yoğurt 1750 kg"), not real packages
MAX_QUANTITY = 100_000  # 100 kg, 100 L or 100000 pieces

# "6x180 ml", "6 x 1,5 L", "4*85 g", "4'lü 100 g" (count is optional), "500 G", "1,5 Lt".
# The number must start a word, so model codes like "XC4010L" are not read as 4010 L.
SIZE = re.compile(
    r"(?<![\w.,])(?:(\d+)\s*(?:x|\*|'li|'lı|'lu|'lü)\s*)?(\d+(?:[.,]\d+)?)\s*(kg|gr|g|lt|l|cl|ml|adet|ürün)\b",
    re.IGNORECASE,
)
# names ending in a bare unit: "Muz Kg", "Avokado Adet"
BARE_UNIT = re.compile(r"\b(kg|adet)$", re.IGNORECASE)
# piece counts: "Yumurta 30'lu", "Avokado Paket 2 li", "Misket Limonu 3lü Paket"
PIECES = re.compile(r"(?<![\w.,])(\d+)\s*'?\s*(?:li|lı|lu|lü)\b", re.IGNORECASE)


def parse_quantity(name):
    """Read the package size from a product name, as (quantity, unit).

    Units are normalised to "g", "ml" or "adet", so "Süt 1 L" -> (1000, "ml"),
    "Gofret 6x36 g" -> (216, "g"), "Muz Kg" -> (1000, "g"), "Avokado Adet" -> (1, "adet"),
    "Yumurta 30'lu" -> (30, "adet").
    Returns (None, None) when the name has no size.
    """
    if not name:
        return None, None
    matches = SIZE.findall(name)
    if matches:
        # the last size in the name is the package size: "Ülker 3+1 Gofret 36 g"
        count, amount, unit = matches[-1]
        unit, multiplier = UNITS[unit.lower()]
        quantity = float(amount.replace(",", ".")) * multiplier * int(count or 1)
        if not 0 < quantity <= MAX_QUANTITY:
            return None, None
        return round(quantity, 3), unit
    bare = BARE_UNIT.search(name.strip())
    if bare:
        # a bare unit means one of it: "Kg" -> 1 kg, "Adet" -> 1 piece
        unit, multiplier = UNITS[bare.group(1).lower()]
        return multiplier, unit
    pieces = PIECES.search(name)
    if pieces:
        return int(pieces.group(1)), "adet"
    return None, None
