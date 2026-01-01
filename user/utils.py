import re
import random
from .models import User
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache


def validate_password(password):
    # define our regex pattern for validation
    pattern = r"^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$"

    # We use the re.match function to test the password against the pattern
    match = re.match(pattern, password)

    # return True if the password matches the pattern, False otherwise
    return bool(match)

def validate_name(name):
    pattern = r"^[A-Za-z]+$"
    name = str(name).strip()
    if len(name) < 3 or not re.match(pattern, name):
        return False
    
    return True

def generate_otp():
    otp=""
    for i in range(6):
        otp+=str(random.randint(0,9))
    return otp

def send_code_to_user(temp_id):
    subject="Email verification OTP"
    otp_code=generate_otp()
    # user=User.objects.get(email=email)
    # user.otp_code = otp_code
    # user.otp_created = timezone.now()
    # user.save()
    current_site="sayit.com"
    email_body=f"hi {str(temp_id).split("@")[0]} thanks for signing up on {current_site} please verify your email with otp {otp_code}.It is valid for 1 minute."
    from_email=settings.EMAIL_HOST_USER
    d_email=EmailMessage(subject=subject,body=email_body,from_email=from_email,to=[temp_id])
    d_email.send(fail_silently=True)
    cache.set(f"otp_{temp_id}", otp_code, timeout=100)

def verify_otp(email, otp_entered):
    otp_cache_key = f"otp_{email}"
    data_cache_key = f"data_{email}"
    user_data = cache.get(data_cache_key)
    otp_code = cache.get(otp_cache_key)

    # check expiry: 1 minute
    if not otp_code:
        return "OTP expired"

    print("kj",otp_code,"dara",user_data)
    if otp_code != otp_entered:
        return "Invalid OTP"
    user=User(
        first_name=user_data["first_name"],
        last_name=user_data["last_name"],
        email=user_data["email"]
    )
    user.set_password(user_data["password"])
    user.is_verified = True
    user.save()

    # Remove cache
    cache.delete(otp_cache_key)
    cache.delete(data_cache_key)

    return "Verified"

def Pass_verify_otp(email, otp_entered):
    otp_cache_key = f"otp_{email}"
    otp_code = cache.get(otp_cache_key)

    # check expiry: 1 minute
    if not otp_code:
        return "OTP expired"

    if otp_code != otp_entered:
        return "Invalid OTP"

    # Remove cache
    cache.delete(otp_cache_key)

    return "Verified"

