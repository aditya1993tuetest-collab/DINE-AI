"""Strict provider-output parsing and candidate membership validation."""

import json
import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

_UNSAFE_TEXT = re.compile(r"[<>]|\[[^]]+\]\([^)]+\)|[\x00-\x08\x0b\x0c\x0e-\x1f]")
_UNSUPPORTED_CLAIM = re.compile(
    r"\b(quiet|family[- ]friendly|child[- ]friendly|fast service|great ambience|romantic)\b",
    re.IGNORECASE,
)


class RankedOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    restaurant_id: str = Field(alias="restaurantId", min_length=1, max_length=100)
    explanation: str = Field(min_length=1, max_length=500)
    caveats: list[str] = Field(default_factory=list, max_length=5)


class ModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ranked: list[RankedOutput] = Field(min_length=1, max_length=50)
    summary: str | None = Field(default=None, max_length=500)


@dataclass(frozen=True, slots=True)
class GuardedRanking:
    ranked: tuple[RankedOutput, ...]
    summary: str | None


class OutputValidationError(ValueError):
    pass


def validate_output(content: str, *, candidate_ids: set[str], result_count: int) -> GuardedRanking:
    try:
        raw = json.loads(content)
        output = ModelOutput.model_validate(raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise OutputValidationError("provider output does not match the ranking schema") from exc
    if len(output.ranked) != result_count:
        raise OutputValidationError("provider returned an unexpected number of results")
    identifiers = [item.restaurant_id for item in output.ranked]
    if len(identifiers) != len(set(identifiers)):
        raise OutputValidationError("provider returned duplicate IDs")
    if not set(identifiers).issubset(candidate_ids):
        raise OutputValidationError("provider returned an unknown ID")
    for item in output.ranked:
        _safe_text(item.explanation)
        if _UNSUPPORTED_CLAIM.search(item.explanation):
            raise OutputValidationError("provider explanation contains an unsupported claim")
        for caveat in item.caveats:
            if not 1 <= len(caveat) <= 250:
                raise OutputValidationError("provider caveat length is invalid")
            _safe_text(caveat)
    if output.summary:
        _safe_text(output.summary)
    return GuardedRanking(tuple(output.ranked), output.summary)


def _safe_text(value: str) -> None:
    if _UNSAFE_TEXT.search(value):
        raise OutputValidationError("provider text must be safe plain text")
