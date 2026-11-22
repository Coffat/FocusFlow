from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.account.infrastructure.email.email_service import EmailService


def _fake_settings(
    *, email_backend: str = "smtp", environment: str = "production"
) -> SimpleNamespace:
    return SimpleNamespace(
        email_backend=email_backend,
        environment=environment,
        email_from="FocusFlow Support <no-reply@focusflow.local>",
        email_host="smtp.example.com",
        email_port=587,
        email_user="mailer",
        email_pass="secret",
        otp_ttl_seconds=300,
        otp_max_attempts=3,
    )


@pytest.mark.asyncio
async def test_smtp_failure_never_leaks_otp_to_stdout_stderr_or_logs(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_otp = "849271"
    settings = _fake_settings(email_backend="smtp", environment="production")

    with (
        caplog.at_level(logging.DEBUG, logger="focusflow.email"),
        patch("src.account.infrastructure.email.email_service.get_settings", return_value=settings),
        patch(
            "src.account.infrastructure.email.email_service.aiosmtplib.send",
            new=AsyncMock(side_effect=RuntimeError("SMTP connection refused")),
        ),
        pytest.raises(RuntimeError, match="SMTP connection refused"),
    ):
        await EmailService.send_otp_email(
            to_email="learner@example.com",
            otp_code=secret_otp,
            purpose="register",
        )

    captured = capsys.readouterr()
    assert secret_otp not in captured.out
    assert secret_otp not in captured.err
    assert secret_otp not in caplog.text


@pytest.mark.asyncio
async def test_valid_smtp_send_succeeds_without_printing_otp(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_otp = "513904"
    settings = _fake_settings(email_backend="smtp", environment="production")
    mock_send = AsyncMock(return_value=({}, "250 OK"))

    with (
        caplog.at_level(logging.DEBUG, logger="focusflow.email"),
        patch("src.account.infrastructure.email.email_service.get_settings", return_value=settings),
        patch("src.account.infrastructure.email.email_service.aiosmtplib.send", new=mock_send),
    ):
        await EmailService.send_otp_email(
            to_email="learner@example.com",
            otp_code=secret_otp,
            purpose="reset_password",
        )

    mock_send.assert_awaited_once()
    captured = capsys.readouterr()
    assert secret_otp not in captured.out
    assert secret_otp not in captured.err
    assert secret_otp not in caplog.text


@pytest.mark.asyncio
async def test_console_backend_in_production_does_not_print_plaintext_otp(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_otp = "902184"
    settings = _fake_settings(email_backend="console", environment="production")

    with (
        caplog.at_level(logging.WARNING, logger="focusflow.email"),
        patch("src.account.infrastructure.email.email_service.get_settings", return_value=settings),
    ):
        await EmailService.send_otp_email(
            to_email="learner@example.com",
            otp_code=secret_otp,
            purpose="register",
        )

    captured = capsys.readouterr()
    assert secret_otp not in captured.out
    assert secret_otp not in captured.err
    assert secret_otp not in caplog.text
    assert len(caplog.records) >= 1
