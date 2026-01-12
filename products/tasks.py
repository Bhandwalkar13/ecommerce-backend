from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_order_email_task(user_email, order_id, amount, tracking):
    subject = f"Order #{order_id} Confirmed! 🎉"
    message = f"""
    Thank you for your order!
    
    Order ID: #{order_id}
    Total Amount: ₹{amount}
    Tracking Number: {tracking}
    
    We'll notify you when your order ships.
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user_email],
            fail_silently=False
        )
    except Exception as e:
        print(f"Email failed: {e}")
