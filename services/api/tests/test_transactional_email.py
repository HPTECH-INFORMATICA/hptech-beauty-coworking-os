"""Tests for transactional invitation e-mail configuration."""
import pytest

from bcos_api.notifications.email import EmailSettings


def test_email_settings_require_all_production_values(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("RESEND_API_KEY", "EMAIL_FROM", "FRONTEND_PUBLIC_URL"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="RESEND_API_KEY"):
        EmailSettings.from_env()


def test_email_settings_normalize_frontend_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("EMAIL_FROM", "BCOS <noreply@example.com>")
    monkeypatch.setenv("FRONTEND_PUBLIC_URL", "https://bcos.example.com/")
    settings = EmailSettings.from_env()
    assert settings.frontend_public_url == "https://bcos.example.com"
