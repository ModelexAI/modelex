# modelex_adapter/payment.py

import jwt  # PyJWT
import requests

# Example secret for demo — in production, use your Modelex signing key!
SECRET_KEY = "MODELEX_SECRET"

def verify_jwt(token: str, min_amount: float) -> bool:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        amount = float(payload.get("amount", 0))
        if amount >= min_amount:
            print(f"[Modelex] JWT verified, amount: {amount}")
            return True
        else:
            print(f"[Modelex] JWT amount too low: {amount} < {min_amount}")
            return False
    except Exception as e:
        print(f"[Modelex] JWT verification failed: {e}")
        return False

def verify_onchain(wallet_address: str, min_amount: float) -> bool:
    """
    Example: Calls your blockchain indexer or Solana RPC node
    to confirm payment has occurred.
    """
    # Replace with your actual on-chain logic!
    solana_rpc = "https://api.mainnet-beta.solana.com"
    # Do your lookup here...
    print(f"[Modelex] (Mock) checking on-chain tx for {wallet_address}")
    return True  # Always true for stub
