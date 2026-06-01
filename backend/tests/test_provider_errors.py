import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.provider_errors import classify_provider_error


class FakeOpenAIQuotaError(Exception):
    status_code = 429
    code = "insufficient_quota"


FakeOpenAIQuotaError.__module__ = "openai"


class FakeFalCreditError(Exception):
    status_code = 400


FakeFalCreditError.__module__ = "fal_client"


class FakeOpenAIRateLimitError(Exception):
    status_code = 429


FakeOpenAIRateLimitError.__module__ = "openai"


def test_classifies_openai_quota_as_actionable():
    error = FakeOpenAIQuotaError(
        "You exceeded your current quota, please check your plan and billing details."
    )

    info = classify_provider_error(error)

    assert info.provider == "openai"
    assert info.code == "insufficient_quota"
    assert info.http_status == 402
    assert "OpenAI production key is out of quota" in info.user_message


def test_classifies_fal_credits_as_actionable():
    error = FakeFalCreditError("Insufficient credits. Please add credits to continue.")

    info = classify_provider_error(error)

    assert info.provider == "fal"
    assert info.code == "insufficient_quota"
    assert "FAL image-generation account is out of credits" in info.user_message


def test_classifies_openai_rate_limit_separately_from_quota():
    error = FakeOpenAIRateLimitError("Rate limit reached for requests.")

    info = classify_provider_error(error)

    assert info.provider == "openai"
    assert info.code == "rate_limited"
    assert info.http_status == 429
    assert "rate-limiting" in info.user_message


def test_unknown_provider_error_is_safe():
    info = classify_provider_error(RuntimeError("unexpected stack detail"))

    assert info.provider == "provider"
    assert info.code == "unknown"
    assert "unexpected stack detail" not in info.user_message
    assert "unexpected stack detail" in info.admin_message
