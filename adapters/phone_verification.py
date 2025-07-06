import random
import time
from fastapi import Request

# In-memory stores for demo (use a real DB in production)
phone_verification_store = {}  # phone_number -> (code, timestamp)
verified_phones = {}           # phone_number -> verification timestamp

def request_phone_verification(phone_number: str) -> str:
    """Simulate sending a verification code via SMS."""
    code = str(random.randint(100000, 999999))
    timestamp = time.time()
    print(f"[Demo] Sending SMS to {phone_number}: Your code is {code}")
    phone_verification_store[phone_number] = (code, timestamp)
    return code

def verify_phone_code(phone_number: str, code: str) -> bool:
    """Verify the code sent to the phone number within 10 seconds."""
    entry = phone_verification_store.get(phone_number)
    if not entry:
        return False
    stored_code, timestamp = entry
    now = time.time()
    if code == stored_code and (now - timestamp) <= 10:
        verified_phones[phone_number] = now
        return True
    return False

def check_phone_verified(request: Request) -> bool:
    """Check if the phone number in the request is verified within the last 10 seconds."""
    phone_number = request.headers.get("X-Phone-Number")
    now = time.time()
    verified_time = verified_phones.get(phone_number)
    is_verified = verified_time is not None and (now - verified_time) <= 10
    # Remove expired verifications
    expired = [num for num, t in verified_phones.items() if (now - t) > 10]
    for num in expired:
        del verified_phones[num]
    print(f"[Modelex] Phone verified: {is_verified} for {phone_number}")
    return is_verified
