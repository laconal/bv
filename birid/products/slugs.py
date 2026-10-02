from django.utils.text import slugify

from .models import StoreProduct

_SLUG_MAX_LENGTH = 255

# slugify() keeps ASCII only - without transliterating first, a Cyrillic name
# like "Платье" would come out empty. Russian alphabet + Uzbek Cyrillic extras.
_CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya", "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h",
}


def slug_from_name(name: str) -> str:
    transliterated = "".join(_CYRILLIC_TO_LATIN.get(char, char) for char in name.lower())
    return slugify(transliterated) or "product"


def unique_product_slug(base: str, exclude_id: int | None = None) -> str:
    """
    `base` if no other product has it, else `base-2`, `base-3`, ... - slugs
    are unique across all stores. `exclude_id` is the product being updated,
    so keeping its own slug isn't a conflict. Two simultaneous requests can
    still pick the same value; the DB unique constraint then 409s the loser.
    """
    others = StoreProduct.objects.exclude(id=exclude_id) if exclude_id else StoreProduct.objects.all()
    candidate = base[:_SLUG_MAX_LENGTH]
    n = 2
    while others.filter(slug=candidate).exists():
        suffix = f"-{n}"
        candidate = base[:_SLUG_MAX_LENGTH - len(suffix)] + suffix
        n += 1
    return candidate
