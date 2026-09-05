from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ModelEvidence:
    handle: str
    text: str
    policy_edition: str | None
    injection_risk: bool


@dataclass(frozen=True, slots=True)
class StructuredGenerationRequest:
    task: str
    claim_number: str
    applicable_policy_edition: str
    evidence: list[ModelEvidence]
    correlation_id: str
    prompt_template_version: str
    response_schema_version: str
    response_schema: dict[str, Any] = field(default_factory=dict)
    max_output_tokens: int = 1_200


@dataclass(frozen=True, slots=True)
class ModelGenerationResult:
    content: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float


class ModelProviderError(Exception):
    pass


class ModelProviderTimeout(ModelProviderError):
    pass


class ModelProviderThrottled(ModelProviderError):
    pass


class ModelProvider(Protocol):
    provider_id: str
    model_id: str
    configuration_version: str

    def generate_structured(
        self, request: StructuredGenerationRequest, *, timeout_seconds: float
    ) -> ModelGenerationResult: ...
