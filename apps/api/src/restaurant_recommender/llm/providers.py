"""Deterministic fake and Groq provider adapters."""

import json
from typing import Literal

import httpx

from restaurant_recommender.domain.ranking import (
    ProviderFailure,
    ProviderResponse,
    RankingRequest,
    TokenUsage,
)


class FakeRankingModel:
    model_id = "fake-grounded-v1"

    def __init__(
        self,
        mode: Literal[
            "valid", "malformed", "unknown", "duplicate", "html", "failure", "timeout"
        ] = "valid",
    ) -> None:
        self.mode = mode
        self.calls = 0

    async def rank(self, request: RankingRequest, *, timeout_seconds: float) -> ProviderResponse:
        self.calls += 1
        if self.mode == "failure":
            raise ProviderFailure("transient", "simulated provider failure", retryable=True)
        if self.mode == "timeout":
            raise ProviderFailure("timeout", "simulated timeout", retryable=True)
        if self.mode == "malformed":
            content = "{truncated"
        else:
            identifiers = [
                item.restaurant_id for item in request.candidates[: request.result_count]
            ]
            if self.mode == "unknown":
                identifiers = ["unknown-restaurant"]
            elif self.mode == "duplicate" and identifiers:
                identifiers = [identifiers[0], identifiers[0]]
            explanation = "Grounded in the submitted restaurant facts."
            if self.mode == "html":
                explanation = "<script>alert(1)</script>"
            preferences = json.loads(request.user_payload).get("preferences", {})
            caveats = (
                ["The additional preference is not verified by the supplied facts."]
                if preferences.get("additionalPreferences")
                else []
            )
            content = json.dumps(
                {
                    "ranked": [
                        {
                            "restaurantId": value,
                            "explanation": explanation,
                            "caveats": caveats,
                        }
                        for value in identifiers
                    ],
                    "summary": "Ranked only from submitted candidates.",
                }
            )
        return ProviderResponse(content, self.model_id, f"fake-{self.calls}", TokenUsage(100, 50))


class GroqRankingModel:
    """Groq chat-completions adapter; provider JSON never escapes this module."""

    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model_id: str,
        *,
        max_output_tokens: int,
        reasoning_effort: Literal["low", "medium", "high"] = "low",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ProviderFailure("configuration", "Groq API key is not configured")
        self.api_key = api_key
        self.model_id = model_id
        self.max_output_tokens = max_output_tokens
        self.reasoning_effort = reasoning_effort
        self.transport = transport

    async def rank(self, request: RankingRequest, *, timeout_seconds: float) -> ProviderResponse:
        payload = {
            "model": self.model_id,
            "temperature": 0,
            "max_completion_tokens": self.max_output_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": request.system_instruction},
                {"role": "user", "content": request.user_payload},
            ],
        }
        if self.model_id.startswith("openai/gpt-oss-"):
            payload.update(
                {
                    "reasoning_effort": self.reasoning_effort,
                    "include_reasoning": False,
                }
            )
        try:
            async with httpx.AsyncClient(
                timeout=timeout_seconds, transport=self.transport
            ) as client:
                response = await client.post(
                    self.endpoint,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise ProviderFailure("timeout", "provider timed out", retryable=True) from exc
        except httpx.TransportError as exc:
            raise ProviderFailure(
                "transient", "provider connection failed", retryable=True
            ) from exc
        if response.status_code == 429:
            raise ProviderFailure("rate_limited", "provider rate limited", retryable=True)
        if response.status_code >= 500:
            raise ProviderFailure("transient", "provider unavailable", retryable=True)
        if response.status_code >= 400:
            raise ProviderFailure("rejected", "provider rejected the request")
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            usage = body.get("usage", {})
            return ProviderResponse(
                content=content,
                model_id=body.get("model", self.model_id),
                provider_request_id=response.headers.get("x-request-id") or body.get("id"),
                usage=TokenUsage(
                    int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
                ),
            )
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderFailure("rejected", "provider response contract changed") from exc
