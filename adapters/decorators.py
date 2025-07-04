from fastapi import Request
from fastapi.responses import JSONResponse
from functools import wraps
from .payment import verify_jwt, verify_onchain
from .phone_verification import check_phone_verified

def modelex_paywall(price: float, currency: str = "TRUSD", phone_required: bool = False):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request, **kwargs):
            # 1) Safely get headers
            token = request.headers.get("Authorization")
            wallet = request.headers.get("X-Wallet-Address")

            if token and token.startswith("Bearer "):
                token = token.replace("Bearer ", "")

            paid = False
            if token:
                paid = verify_jwt(token, min_amount=price)
            if not paid and wallet:
                paid = verify_onchain(wallet, min_amount=price)

            if not paid:
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "Payment required",
                        "price": price,
                        "currency": currency,
                        "payment_endpoint": "https://pay.modelex.ai/pay",
                        "phone_required": phone_required
                    }
                )

            # 2) Check phone if needed
            if phone_required and not check_phone_verified(request):
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "Phone verification required",
                        "verify_url": "https://modelex.ai/verify"
                    }
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
