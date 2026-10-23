"""Conservative canonical text normalization rules."""

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_SEPARATORS = re.compile(r"\s*[,;/|]+\s*")


def display_text(value: str | None) -> str | None:
    """Normalize Unicode and whitespace while retaining source casing."""

    if value is None:
        return None
    cleaned = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value)).strip()
    return cleaned or None


def comparison_text(value: str | None) -> str | None:
    """Create a deterministic value for comparisons, never for display."""

    cleaned = display_text(value)
    return cleaned.casefold() if cleaned is not None else None


def cuisine_list(value: str | None) -> tuple[str, ...]:
    """Split known source separators and deduplicate case-insensitively."""

    cleaned = display_text(value)
    if cleaned is None:
        return ()
    result: dict[str, str] = {}
    for part in _SEPARATORS.split(cleaned):
        item = display_text(part)
        if item:
            result.setdefault(item.casefold(), item)
    return tuple(result.values())
