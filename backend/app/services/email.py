from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings


class EmailService:
    """Simple SMTP email service for transactional emails."""

    def __init__(self):
        self.enabled = bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)

    def _send(self, to: str, subject: str, html: str, text: Optional[str] = None) -> bool:
        if not self.enabled:
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg["To"] = to

        if text:
            msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
            return True
        except Exception:
            return False

    def send_verification_email(self, to: str, token: str) -> bool:
        verify_url = f"{settings.allowed_origins[0]}/reset-password?token={token}"
        subject = "Verify your email address"
        html = f"""
        <div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
          <div style="text-align: center; margin-bottom: 24px;">
            <img src="https://omnimigrate.app/logo.png" alt="OmniMigrate" style="height: 40px;">
          </div>
          <h1 style="color: #111;">Verify your email</h1>
          <p>Thanks for signing up! Click the button below to verify your email address.</p>
          <p style="text-align: center; margin: 32px 0;">
            <a href="{verify_url}" style="background: #10b981; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; display: inline-block;">
              Verify Email
            </a>
          </p>
          <p style="color: #666; font-size: 14px;">
            Or copy this link: <a href="{verify_url}">{verify_url}</a>
          </p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
          <p style="color: #999; font-size: 12px;">
            If you didn't create an account, you can safely ignore this email.
          </p>
        </div>
        """
        text = f"Verify your email: {verify_url}"
        return self._send(to, subject, html, text)

    def send_password_reset(self, to: str, token: str) -> bool:
        reset_url = f"{settings.allowed_origins[0]}/reset-password?token={token}"
        subject = "Reset your password"
        html = f"""
        <div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
          <div style="text-align: center; margin-bottom: 24px;">
            <img src="https://omnimigrate.app/logo.png" alt="OmniMigrate" style="height: 40px;">
          </div>
          <h1 style="color: #111;">Reset your password</h1>
          <p>You requested a password reset. Click the button below to set a new password.</p>
          <p style="text-align: center; margin: 32px 0;">
            <a href="{reset_url}" style="background: #10b981; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; display: inline-block;">
              Reset Password
            </a>
          </p>
          <p style="color: #666; font-size: 14px;">
            Or copy this link: <a href="{reset_url}">{reset_url}</a>
          </p>
          <p style="color: #999; font-size: 12px;">
            This link expires in 1 hour. If you didn't request this, ignore this email.
          </p>
        </div>
        """
        text = f"Reset your password: {reset_url}"
        return self._send(to, subject, html, text)

    def send_migration_complete(self, to: str, job_title: str, job_url: str) -> bool:
        subject = f"Migration completed: {job_title}"
        html = f"""
        <div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
          <div style="text-align: center; margin-bottom: 24px;">
            <img src="https://omnimigrate.app/logo.png" alt="OmniMigrate" style="height: 40px;">
          </div>
          <h1 style="color: #111;">Migration Complete</h1>
          <p>Your migration job <strong>{job_title}</strong> has finished successfully.</p>
          <p style="text-align: center; margin: 32px 0;">
            <a href="{job_url}" style="background: #10b981; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; display: inline-block;">
              View Results
            </a>
          </p>
        </div>
        """
        text = f"Migration complete: {job_title}. View at {job_url}"
        return self._send(to, subject, html, text)


email_service = EmailService()