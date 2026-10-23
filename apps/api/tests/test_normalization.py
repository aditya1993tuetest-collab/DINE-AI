from decimal import Decimal

from restaurant_recommender.domain.normalization import comparison_text, cuisine_list, display_text
from restaurant_recommender.ingestion.normalize import normalize_row


def row(**changes: str | None) -> dict[str, str | None]:
    value: dict[str, str | None] = {
        "url": "https://EXAMPLE.test/place/demo?tracking=1",
        "address": " 1  Main Road ",
        "name": " Café  Démo ",
        "online_order": "Yes",
        "book_table": "No",
        "rate": "4.25 / 5",
        "votes": "10",
        "location": " IndiraNagar ",
        "rest_type": "Cafe, Quick Bites",
        "cuisines": " Café; Italian, café ",
        "approx_cost(for two people)": "₹1,200",
        "listed_in(type)": "Cafes",
        "listed_in(city)": "Indiranagar",
    }
    value.update(changes)
    return value


def test_text_and_cuisine_normalization() -> None:
    assert display_text("  Café\tDémo ") == "Café Démo"
    assert comparison_text(" Straße ") == "strasse"
    assert cuisine_list("Italian; Cafe | italian") == ("Italian", "Cafe")


def test_valid_row_preserves_display_and_builds_comparison_values() -> None:
    result = normalize_row(row())
    assert result.rejection_codes == ()
    assert result.restaurant is not None
    assert result.restaurant.name == "Café Démo"
    assert result.restaurant.name_normalized == "café démo"
    assert result.restaurant.source_key == "https://example.test/place/demo"
    assert result.restaurant.rating is not None
    assert result.restaurant.rating.value == Decimal("4.25")
    assert result.restaurant.cost is not None
    assert result.restaurant.cost.minor_units == 120_000
    assert result.restaurant.cuisines == ("Café", "Italian")


def test_unrated_and_missing_cost_are_accepted_as_unavailable() -> None:
    result = normalize_row(row(rate="NEW", **{"approx_cost(for two people)": ""}))
    assert result.restaurant is not None
    assert result.restaurant.rating is None
    assert result.restaurant.cost is None


def test_malformed_optional_values_are_warnings() -> None:
    result = normalize_row(
        row(rate="6/5", votes="-1", **{"approx_cost(for two people)": "about 500"})
    )
    assert result.restaurant is not None
    assert set(result.warning_codes) == {"INVALID_RATING", "INVALID_COST", "INVALID_VOTES"}


def test_required_identity_fields_are_rejected() -> None:
    result = normalize_row(row(name=" ", location=None, cuisines=None, url="javascript:no"))
    assert result.restaurant is None
    assert set(result.rejection_codes) == {
        "MISSING_NAME",
        "MISSING_LOCATION",
        "MISSING_CUISINE",
        "MISSING_SOURCE_KEY",
    }
