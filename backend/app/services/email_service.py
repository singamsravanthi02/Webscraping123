import logging
import httpx
import time
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

    @abstractmethod
    def send_otp_email(self, email: str, otp: str) -> None:
        pass

class ConsoleEmailService(BaseEmailService):
    """A dummy email service that prints to console for development or fallback."""
    def send_welcome_email(self, email: str, full_name: str) -> None:
        logger.info(f"Sending welcome email to {full_name} <{email}>")

    def send_password_reset_email(self, email: str, reset_token: str) -> None:
        logger.info(f"[DEBUG SPRINT] Password reset token for {email} is {reset_token}")
        with open("latest_otp.txt", "w") as f:
            f.write(reset_token)
        logger.info(f"Sending password reset token {reset_token} to {email}")

    def send_otp_email(self, email: str, otp: str) -> None:
        logger.info(f"Sending OTP {otp} to {email}")

class BrevoEmailService(BaseEmailService):
    """Production email service using Brevo (Sendinblue)."""
    def __init__(self):
        self.api_key = settings.BREVO_API_KEY
        self.sender_email = settings.EMAIL_FROM
        self.sender_name = settings.EMAIL_FROM_NAME
        self.api_url = "https://api.brevo.com/v3/smtp/email"

    def _send(self, to_email: str, subject: str, html_content: str):
        headers = {
            "accept": "application/json",
            "api-key": self.api_key,
            "content-type": "application/json"
        }
        
        payload = {
            "sender": {"name": self.sender_name, "email": self.sender_email},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_content
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # We use a synchronous client here because the surrounding code in auth_service is currently synchronous.
                # In a high throughput scenario, this could be dispatched to Celery.
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(self.api_url, headers=headers, json=payload)
                    response.raise_for_status()
                    msg = f"Email sent successfully to {to_email}. Message ID: {response.json().get('messageId')}"
                    logger.info(msg)
                    print(msg, flush=True)
                    return True
            except httpx.HTTPStatusError as e:
                err = f"Brevo API error on attempt {attempt + 1}: {e.response.text}"
                logger.error(err)
                print(err, flush=True)
            except Exception as e:
                err = f"Failed to send email on attempt {attempt + 1}: {str(e)}"
                logger.error(err)
                print(err, flush=True)
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt) # Exponential backoff
                
        logger.error(f"Failed to send email to {to_email} after {max_retries} attempts.")
        return False

    def send_welcome_email(self, email: str, full_name: str) -> None:
        html = f"""
        <div style="font-family: sans-serif; padding: 20px;">
            <h2 style="color: #4F46E5;">Welcome to SPIP!</h2>
            <p>Hi {full_name},</p>
            <p>Your account has been successfully verified. You can now access your dashboard and start preparing for your career.</p>
            <p>Best regards,<br>The SPIP Team</p>
        </div>
        """
        self._send(email, "Welcome to SPIP!", html)

    def send_password_reset_email(self, email: str, reset_token: str) -> None:
        logger.info(f"[DEBUG SPRINT] Password reset token for {email} is {reset_token}")
        with open("latest_otp.txt", "w") as f:
            f.write(reset_token)
        html = f"""
        <div style="font-family: sans-serif; padding: 20px;">
            <h2 style="color: #4F46E5;">Password Reset Request</h2>
            <p>We received a request to reset your password. Here is your 6-digit reset code:</p>
            <h1 style="font-size: 32px; letter-spacing: 5px; color: #111827;">{reset_token}</h1>
            <p>This code will expire in 10 minutes. If you did not request this, please ignore this email.</p>
        </div>
        """
        self._send(email, "Password Reset Code", html)

    def send_otp_email(self, email: str, otp: str) -> None:
        logger.info(f"[DEBUG SPRINT] OTP for {email} is {otp}")
        with open("latest_otp.txt", "w") as f:
            f.write(otp)
        html = f"""
        <div style="font-family: sans-serif; padding: 20px;">
            <h2 style="color: #4F46E5;">Verify your Email</h2>
            <p>Thank you for registering. Please use the following 6-digit verification code to complete your registration:</p>
            <h1 style="font-size: 32px; letter-spacing: 5px; color: #111827;">{otp}</h1>
            <p>This code will expire in 10 minutes.</p>
        </div>
        """
        self._send(email, "Verify Your Account", html)

# Graceful Degradation Logic
def get_email_service() -> BaseEmailService:
    if settings.BREVO_API_KEY:
        return BrevoEmailService()
    else:
        logger.warning("BREVO_API_KEY not configured. Falling back to ConsoleEmailService.")
        return ConsoleEmailService()

email_service = get_email_service()

