import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from app.core.config import settings
from app.services.email.emailConfig import email_api


def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
) -> None:
    sender_email = settings.EMAIL_FROM or settings.BREVO_SENDER_EMAIL
    sender_name = settings.BREVO_SENDER_NAME or "ai_need_detection"

    if not settings.brevo_api_key or not sender_email:
        raise RuntimeError(
            "Brevo is not configured. Set BREVO_API_KEY (or EMAIL_BREVO_API_KEY) and EMAIL_FROM in .env"
        )

    recipient = {"email": to_email, "name": to_name}

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        sender={
            "name": sender_name,
            "email": sender_email,
        },
        to=[recipient],
        subject=subject,
        html_content=html_content,
    )

    try:
        email_api.send_transac_email(send_smtp_email)
    except ApiException as error:
        raise RuntimeError(f"Brevo request failed: {error}") from error
