import os
import django
from django.core.mail import send_mail
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'animal_intrusion.settings')
django.setup()

def test_email():
    print(f"Testing email configuration...")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    
    recipient = settings.EMAIL_HOST_USER  # Send to self
    if not recipient or 'your-real-email' in recipient:
        print("ERROR: EMAIL_HOST_USER is not configured in settings.py!")
        return

    try:
        print(f"Attempting to send email to {recipient}...")
        send_mail(
            subject='Test Email from Animal Intrusion System',
            message='If you are reading this, your email configuration is working correctly! ✅',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email.")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_email()
