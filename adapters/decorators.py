import asyncio
import time
from functools import wraps
from typing import Optional, Callable
from fastapi import Request
from fastapi.responses import JSONResponse

from adapters.payment import verify_jwt, verify_onchain
from adapters.phone_verification import check_phone_verified
#from adapters.crawler_identification import identify_crawler


def modelex_paywall(
    price: float
) -> Callable:
    """
    Decorator to enforce phone verification and payment requirements on FastAPI endpoints.
    Args:
        price: price required for the request
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request, **kwargs):
            phone_number: Optional[str] = request.headers.get("X-Phone-Number")
            token = _extract_auth_token(request)
            wallet = request.headers.get("X-Wallet-Address")
            if not check_phone_verified(request):
                return JSONResponse(
                    status_code=403,
                    content={"error": "Request forfeited: phone number not verified."}
                )
            # Phone is verified, now check for payment linked to this phone number
            jwt_valid = token and verify_jwt(token, min_amount=price, phone_number=phone_number)
            wallet_valid = wallet and verify_onchain(wallet, min_amount=price, phone_number=phone_number)
            if jwt_valid or wallet_valid:
                return await func(*args, **kwargs)
            else:
                return JSONResponse(
                    status_code=402,
                    content={
                        "paywall": True,
                        "price": price,
                        "currency": "TRUSD",
                        "message": "Payment required to access this resource."
                    }
                )
        return wrapper
    return decorator


def _extract_auth_token(request: Request) -> Optional[str]:
    """Extract and clean authorization token from request headers."""
    token = request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        return token.replace("Bearer ", "")
    return token
