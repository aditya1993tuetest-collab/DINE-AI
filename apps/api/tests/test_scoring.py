import uuid
from dataclasses import replace
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from restaurant_recommender.domain.recommendations import (
    BudgetRange,
    Candidate,
    RecommendationQuery,
    ScoringConfig,
    rank_candidates,
    score_candidate,
)
from restaurant_recommender.recommendation_service import explanation


def candidate(*, name: str = "Demo", rating: str = "4.0", votes: int = 100) -> Candidate:
    return Candidate(
        uuid.uuid4(),
        f"key-{name}",
        name,
        "Bangalore",
        "bangalore",
        "Indiranagar",
        "indiranagar",
        ("Italian",),
        ("italian",),
        100_000,
        "INR",
        Decimal(rating),
        Decimal("5"),
        votes,
        "https://example.test/demo",
    )


def query() -> RecommendationQuery:
    return RecommendationQuery(
        "bangalore",
        "indiranagar",
        ("italian",),
        BudgetRange(50_000, 150_000, "INR"),
        Decimal("3.5"),
        None,
        5,
    )


def test_every_score_term_is_bounded_and_repeatable() -> None:
    first = score_candidate(candidate(), query(), ScoringConfig())
    second = score_candidate(candidate(), query(), ScoringConfig())
    assert first == second
    assert all(
        0 <= value <= 1
        for value in (
            first.location,
            first.cuisine,
            first.budget,
            first.rating,
            first.confidence,
            first.completeness,
            first.total,
        )
    )


def test_stable_tie_breakers_prefer_rating_votes_then_name() -> None:
    values = [
        candidate(name="Zulu", rating="4.0", votes=10),
        candidate(name="Alpha", rating="4.0", votes=10),
        candidate(name="Higher", rating="4.5", votes=10),
    ]
    ranked = rank_candidates(values, query(), ScoringConfig())
    assert [item.candidate.name for item in ranked] == ["Higher", "Alpha", "Zulu"]


def test_deterministic_explanation_uses_only_verified_facts_and_caveats() -> None:
    value = candidate()
    requested = RecommendationQuery(
        "bangalore",
        "indiranagar",
        ("italian",),
        BudgetRange(50_000, 150_000, "INR"),
        Decimal("3.5"),
        "quiet dinner",
        5,
    )
    scored = rank_candidates([value], requested, ScoringConfig())[0]
    message, caveats = explanation(scored, requested)
    assert "Italian" in message
    assert "budget" in message
    assert "4.0/5" in message
    assert "Indiranagar" in message
    assert caveats == [
        "The additional free-form preference cannot be verified from the source data."
    ]


def test_deterministic_explanation_handles_minimal_request() -> None:
    requested = RecommendationQuery("bangalore", None, (), None, None, None, 5)
    minimal = replace(candidate(), locality=None, locality_normalized=None)
    scored = rank_candidates([minimal], requested, ScoringConfig())[0]
    message, caveats = explanation(scored, requested)
    assert "satisfies the structured request" in message
    assert caveats == []


def test_missing_optional_facts_do_not_gain_score() -> None:
    value = candidate()
    missing = Candidate(
        value.id,
        value.source_key,
        value.name,
        value.city,
        value.city_normalized,
        None,
        None,
        (),
        (),
        None,
        None,
        None,
        Decimal("5"),
        None,
        value.source_url,
    )
    score = score_candidate(missing, query(), ScoringConfig())
    assert score.location == 0
    assert score.cuisine == 0
    assert score.budget == 0
    assert score.rating == 0
    assert score.completeness == 0


@given(
    rating=st.decimals(min_value="0", max_value="5", places=2, allow_nan=False),
    votes=st.integers(min_value=0, max_value=1_000_000),
    cost=st.integers(min_value=0, max_value=10_000_000),
)
def test_score_range_property(rating: Decimal, votes: int, cost: int) -> None:
    base = candidate(rating=str(rating), votes=votes)
    generated = Candidate(
        base.id,
        base.source_key,
        base.name,
        base.city,
        base.city_normalized,
        base.locality,
        base.locality_normalized,
        base.cuisines,
        base.cuisines_normalized,
        cost,
        base.currency_code,
        rating,
        base.rating_scale,
        votes,
        base.source_url,
    )
    score = score_candidate(generated, query(), ScoringConfig())
    assert all(
        0 <= value <= 1
        for value in (
            score.location,
            score.cuisine,
            score.budget,
            score.rating,
            score.confidence,
            score.completeness,
            score.total,
        )
    )
