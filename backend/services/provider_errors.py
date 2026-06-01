"""Classify provider failures into actionable, user-safe errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderErrorInfo:
    provider: str
    code: str
    user_message: str
    admin_message: str
    http_status: int = 503

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "code": self.code,
            "message": self.user_message,
            "admin_message": self.admin_message,
        }


def classify_provider_error(exc: Exception) -> ProviderErrorInfo:
    """Return a stable provider error for logs, API responses, and SMS fallbacks."""
    text = _stringify_exception(exc)
    text_lower = text.lower()
    provider = _detect_provider(exc, text_lower)
    status_code = _status_code(exc)

    if _is_quota_error(text_lower):
        return _quota_error(provider, text, status_code)

    if status_code == 429 or "rate limit" in text_lower or "too many requests" in text_lower:
        return ProviderErrorInfo(
            provider=provider,
            code="rate_limited",
            user_message=(
                f"I'm blocked because {provider} is rate-limiting requests. "
                "Wait a minute, then retry."
            ),
            admin_message=text,
            http_status=429,
        )

    if status_code in (401, 403) or any(
        marker in text_lower
        for marker in ("invalid api key", "incorrect api key", "unauthorized", "forbidden", "authentication")
    ):
        return ProviderErrorInfo(
            provider=provider,
            code="auth_failed",
            user_message=(
                f"I'm blocked because the {provider} production key is missing or invalid. "
                "Check the production environment variable and retry."
            ),
            admin_message=text,
            http_status=503,
        )

    if any(marker in text_lower for marker in ("timeout", "timed out", "deadline exceeded")):
        return ProviderErrorInfo(
            provider=provider,
            code="timeout",
            user_message=(
                f"{provider} timed out before I could finish. Try again in a minute."
            ),
            admin_message=text,
            http_status=504,
        )

    if status_code in (500, 502, 503, 504):
        return ProviderErrorInfo(
            provider=provider,
            code="provider_unavailable",
            user_message=(
                f"{provider} is temporarily failing upstream. Try again shortly."
            ),
            admin_message=text,
            http_status=503,
        )

    return ProviderErrorInfo(
        provider=provider,
        code="unknown",
        user_message="I hit a backend provider error. Check the logs, then retry.",
        admin_message=text,
        http_status=503,
    )


def _quota_error(provider: str, text: str, status_code: int | None) -> ProviderErrorInfo:
    if provider == "fal":
        user_message = (
            "I'm blocked because the FAL image-generation account is out of credits. "
            "Add FAL credits, then retry."
        )
    elif provider == "openai":
        user_message = (
            "I'm blocked because the OpenAI production key is out of quota. "
            "Add credits or update billing, then retry."
        )
    else:
        user_message = (
            f"I'm blocked because {provider} is out of quota or credits. "
            "Add provider credits, then retry."
        )

    return ProviderErrorInfo(
        provider=provider,
        code="insufficient_quota",
        user_message=user_message,
        admin_message=text,
        http_status=402 if status_code in (None, 400, 429) else status_code,
    )


def _is_quota_error(text_lower: str) -> bool:
    return any(
        marker in text_lower
        for marker in (
            "insufficient_quota",
            "exceeded your current quota",
            "out of quota",
            "insufficient quota",
            "billing details",
            "insufficient credits",
            "out of credits",
            "insufficient balance",
        )
    )


def _detect_provider(exc: Exception, text_lower: str) -> str:
    module = exc.__class__.__module__.lower()
    class_name = exc.__class__.__name__.lower()
    combined = f"{module} {class_name} {text_lower}"

    if "openai" in combined or "gpt-image" in combined or "gpt image" in combined:
        return "openai"
    if "fal" in combined or "flux" in combined:
        return "fal"
    if "twilio" in combined:
        return "twilio"
    if "anthropic" in combined or "claude" in combined:
        return "anthropic"
    return "provider"


def _status_code(exc: Exception) -> int | None:
    for attr in ("status_code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    if isinstance(value, int):
        return value
    return None


def _stringify_exception(exc: Exception) -> str:
    pieces = [str(exc)]
    for attr in ("code", "type", "body"):
        value = getattr(exc, attr, None)
        if value:
            pieces.append(f"{attr}={value}")
    return " | ".join(pieces)
