import logging
from email.message import EmailMessage

import aiosmtplib

from src.shared_kernel.config import get_settings

logger = logging.getLogger("focusflow.email")


class EmailService:
    """Asynchronous Email Delivery Service supporting SMTP (Mailpit / Gmail) and Console fallback."""

    @staticmethod
    async def send_otp_email(to_email: str, otp_code: str, purpose: str) -> None:
        """Send verification OTP email via configured backend."""
        settings = get_settings()

        subject_title = (
            "FocusFlow — Mã xác thực đăng ký tài khoản"
            if purpose == "register"
            else "FocusFlow — Mã xác thực đặt lại mật khẩu"
        )
        purpose_label = (
            "đăng ký tài khoản học tập" if purpose == "register" else "đặt lại mật khẩu tài khoản"
        )

        # 1. Console / Defense Demo Mode
        if settings.email_backend.lower() == "console":
            print("\n" + "=" * 60)
            print(f" [MOCK EMAIL DISPATCH] To: {to_email}")
            print(f" Subject: {subject_title}")
            print(f" Purpose: {purpose_label}")
            print(
                f" >>> OTP CODE: [ {otp_code} ] (Valid for {settings.otp_ttl_seconds // 60} minutes) <<<"
            )
            print("=" * 60 + "\n")
            return

        # 2. SMTP Real Email Dispatch (Supports Mailpit on localhost:1025 and production SMTP)
        msg = EmailMessage()
        msg["From"] = settings.email_from
        msg["To"] = to_email
        msg["Subject"] = subject_title

        plain_text = f"""Xin chào,

Bạn vừa yêu cầu mã xác thực OTP để {purpose_label} trên nền tảng FocusFlow.

Mã xác thực của bạn là: {otp_code}

Mã này có hiệu lực trong vòng {settings.otp_ttl_seconds // 60} phút và chỉ sử dụng được 1 lần duy nhất.
Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email.

Trân trọng,
Đội ngũ phát triển FocusFlow
"""

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; }}
    .container {{ max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
    .brand {{ font-size: 22px; font-weight: 700; color: #0f172a; margin-bottom: 24px; letter-spacing: -0.5px; }}
    .brand span {{ color: #4338ca; }}
    .heading {{ font-size: 18px; font-weight: 600; color: #1e293b; margin-bottom: 12px; }}
    .description {{ font-size: 14px; color: #475569; line-height: 1.6; margin-bottom: 24px; }}
    .otp-box {{ background-color: #f1f5f9; border-radius: 8px; padding: 18px; text-align: center; margin-bottom: 24px; border: 1px dashed #cbd5e1; }}
    .otp-code {{ font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #4338ca; font-family: 'Courier New', Courier, monospace; }}
    .expiry {{ font-size: 12px; color: #64748b; margin-top: 8px; }}
    .footer {{ font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 16px; margin-top: 24px; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="brand">Focus<span>Flow</span></div>
    <div class="heading">Mã xác thực một lần (OTP)</div>
    <p class="description">
      Bạn vừa yêu cầu mã xác thực để <strong>{purpose_label}</strong> trên nền tảng FocusFlow. Vui lòng nhập mã bên dưới để tiếp tục:
    </p>
    <div class="otp-box">
      <div class="otp-code">{otp_code}</div>
      <div class="expiry">Mã có hiệu lực trong {settings.otp_ttl_seconds // 60} phút &bull; Tối đa {settings.otp_max_attempts} lần nhập sai</div>
    </div>
    <p class="description" style="font-size: 13px;">
      Vì lý do an toàn, tuyệt đối không chia sẻ mã này với bất kỳ ai. Nếu bạn không gửi yêu cầu này, vui lòng bỏ qua email.
    </p>
    <div class="footer">
      &copy; 2026 FocusFlow &bull; Adaptive Self-Directed Learning OS
    </div>
  </div>
</body>
</html>"""

        msg.set_content(plain_text)
        msg.add_alternative(html_content, subtype="html")

        # Determine start_tls based on port and credentials (Mailpit 1025 has no TLS)
        is_mailpit = settings.email_port in (1025, 25) or settings.email_host in (
            "localhost",
            "127.0.0.1",
            "mailpit",
        )
        use_start_tls = not is_mailpit and bool(settings.email_user)

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.email_host,
                port=settings.email_port,
                username=settings.email_user or None,
                password=settings.email_pass or None,
                start_tls=use_start_tls,
                timeout=12.0,
            )
            logger.info("OTP email successfully dispatched to %s", to_email)
        except Exception as exc:
            logger.error("Failed to send OTP email via SMTP to %s: %s", to_email, str(exc))
            # Fallback output to stdout for defense stability
            print(f"\n[SMTP ERROR FALLBACK] OTP for {to_email} is: {otp_code}\n")
            raise
