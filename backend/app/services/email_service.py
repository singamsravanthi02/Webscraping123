import logging
from abc import ABC, abstractmethod
from app.core.config import settings

logger = logging.getLogger(__name__)

class BaseEmailService(ABC):
    @abstractmethod
    def send_welcome_email(self, email: str, full_name: str) -> None:
        pass

    @abstractmethod
    def send_password_reset_email(self, email: str, reset_token: str) -> None:
        pass

class ConsoleEmailService(BaseEmailService):
    """A dummy email service that prints to console for development or fallback."""
    def send_welcome_email(self, email: str, full_name: str) -> None:
        logger.info(f"Sending welcome email to {full_name} <{email}>")

    def send_password_reset_email(self, email: str, reset_token: str) -> None:
        logger.info(f"Sending password reset token {reset_token} to {email}")

class BrevoEmailService(BaseEmailService):
    """Production email service using Brevo (Sendinblue)."""
    def __init__(self):
        self.api_key = settings.BREVO_API_KEY
        self.sender_email = settings.EMAIL_FROM
        self.sender_name = settings.EMAIL_FROM_NAME

    def _send(self, to_email: str, subject: str, html_content: str):
        # Implementation of Brevo HTTP API or SDK would go here
        # E.g. requests.post("https://api.brevo.com/v3/smtp/email", headers={"api-key": self.api_key})
        logger.info(f"Brevo is sending email to {to_email} with subject: {subject}")

    def send_welcome_email(self, email: str, full_name: str) -> None:
        self._send(email, "Welcome to SPIP!", f"<p>Hi {full_name}, welcome!</p>")

    def send_password_reset_email(self, email: str, reset_token: str) -> None:
        self._send(email, "Password Reset", f"<p>Your reset token is: {reset_token}</p>")

# Graceful Degradation Logic
def get_email_service() -> BaseEmailService:
    if settings.BREVO_API_KEY:
        return BrevoEmailService()
    else:
        logger.warning("BREVO_API_KEY not configured. Falling back to ConsoleEmailService.")
        return ConsoleEmailService()

email_service = get_email_service()
