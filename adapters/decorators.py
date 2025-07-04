from fastapi import Request
from fastapi.responses import JSONResponse
from functools import wraps
from .payment import verify_jwt, verify_onchain
from .phone_verification import check_phone_verified
import yaml
from functools import wraps
from langchain.schema import LLMResult

from solana.rpc.api import Client as SolanaClient

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


import yaml
from functools import wraps
from langchain.schema import LLMResult

from solana.rpc.api import Client as SolanaClient  # or your preferred Solana SDK

# Load Modelex config once
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

AGENT_WALLET = config["wallet_address"]
RATE_PER_TOKEN = config["rate_per_token"]
CURRENCY = config["currency"]
NETWORK = config["network"]

# Optional: initialize your Solana client
solana_client = SolanaClient("https://api.mainnet-beta.solana.com")

