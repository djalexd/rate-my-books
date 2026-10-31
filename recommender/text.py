import re
import unicodedata
from typing import Optional, Tuple


def normalize(text: str) -> str:
    """Lowercase, strip accents and punctuation, collapse whitespace."""
    decomposed = unicodedata.normalize('NFKD', text)
    stripped = ''.join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', stripped.lower())).strip()


def split_title_author(name: str) -> Tuple[str, Optional[str]]:
    """Split a 'Title - Author' file name; the author is whatever follows the last ' - '."""
    if ' - ' not in name:
        return name.strip(), None
    title, author = name.rsplit(' - ', 1)
    return title.strip(), author.strip() or None
