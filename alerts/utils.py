import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

def send_alert_email(user, subject, message):
    """
    Sends an email to the user.
    Returns True if successful, False otherwise.
    Wraps in try/except to prevent crashing the calling process.
    """
    if not user.email:
        logger.warning(f"Cannot send email: User {user.username} has no email address.")
        return False

    try:
        logger.info(f"Sending email to {user.email}: {subject}")
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False, 
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {user.email}: {e}")
        return False
