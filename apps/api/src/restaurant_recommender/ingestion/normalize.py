"""Raw Zomato record normalization and rejection policy."""

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit, urlunsplit

from restaurant_recommender.domain.models import CanonicalRestaurant, Money, Rating
from restaurant_recommender.domain.normalization import comparison_text, cuisine_list, display_text

_MISSING = {"", "-", "n/a", "na", "none", "null", "new", "not rated", "not-rated"}
_RATING = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*$")
_COST = re.compile(r"^\s*(?:₹|inr\s*)?([0-9][0-9,]*)\s*$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    restaurant: CanonicalRestaurant | None
    rejection_codes: tuple[str, ...] = ()
    warning_codes: tuple[str, ...] = ()


def _missing(value: str | None) -> bool:
    return value is None or value.strip().casefold() in _MISSING


def _source_url(value: str | None) -> str | None:
    if _missing(value):
        return None
    assert value is not None
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", "")
    )


def _rating(value: str | None) -> tuple[Rating | None, str | None]:
    if _missing(value):
        return None, None
    match = _RATING.match(value or "")
    if not match:
        return None, "INVALID_RATING"
    try:
        return Rating(Decimal(match.group(1)), Decimal(match.group(2))), None
    except (InvalidOperation, ValueError):
        return None, "INVALID_RATING"


def _cost(value: str | None) -> tuple[Money | None, str | None]:
    if _missing(value):
        return None, None
    match = _COST.match(value or "")
    if not match:
        return None, "INVALID_COST"
    rupees = int(match.group(1).replace(",", ""))
    return Money(rupees * 100, "INR"), None


def _votes(value: str | None) -> tuple[int | None, str | None]:
    if _missing(value):
        return None, None
    try:
        votes = int(value or "")
    except ValueError:
        return None, "INVALID_VOTES"
    return (votes, None) if votes >= 0 else (None, "INVALID_VOTES")


def normalize_row(row: Mapping[str, str | None]) -> NormalizationResult:
    name = display_text(row.get("name"))
    locality = display_text(row.get("location"))
    cuisines = cuisine_list(row.get("cuisines"))
    url = _source_url(row.get("url"))
    rejection: list[str] = []
    if name is None:
        rejection.append("MISSING_NAME")
    if locality is None:
        rejection.append("MISSING_LOCATION")
    if not cuisines:
        rejection.append("MISSING_CUISINE")
    if url is None:
        rejection.append("MISSING_SOURCE_KEY")
    if rejection:
        return NormalizationResult(None, tuple(rejection))

    rating, rating_warning = _rating(row.get("rate"))
    cost, cost_warning = _cost(row.get("approx_cost(for two people)"))
    votes, votes_warning = _votes(row.get("votes"))
    warnings = tuple(x for x in (rating_warning, cost_warning, votes_warning) if x)
    source_payload = json.dumps(
        dict(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    attributes = {
        "online_order": comparison_text(row.get("online_order")) == "yes",
        "book_table": comparison_text(row.get("book_table")) == "yes",
        "restaurant_types": cuisine_list(row.get("rest_type")),
        "listing_type": display_text(row.get("listed_in(type)")),
    }
    assert name is not None and locality is not None and url is not None
    return NormalizationResult(
        CanonicalRestaurant(
            source_key=url,
            name=name,
            name_normalized=comparison_text(name) or "",
            city="Bangalore",
            city_normalized="bangalore",
            locality=locality,
            locality_normalized=comparison_text(locality),
            address=display_text(row.get("address")),
            cuisines=cuisines,
            cost=cost,
            rating=rating,
            votes=votes,
            attributes=attributes,
            source_url=url,
            source_payload_hash=hashlib.sha256(source_payload.encode()).hexdigest(),
        ),
        warning_codes=warnings,
    )
