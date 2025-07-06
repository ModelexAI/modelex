# modelex_adapter/payment.py

import jwt  # PyJWT
import requests
from solana.rpc.api import Client as SolanaClient
from solana.publickey import PublicKey
from typing import Optional

# Example secret for demo — in production, use your Modelex signing key!
SECRET_KEY = "MODELEX_SECRET"

def verify_jwt(token: str, min_amount: float, phone_number: Optional[str] = None) -> bool:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        amount = float(payload.get("amount", 0))
        if amount >= min_amount:
            if phone_number is not None:
                jwt_phone = payload.get("phone_number")
                if jwt_phone != phone_number:
                    print(f"[Modelex] JWT phone mismatch: {jwt_phone} != {phone_number}")
                    return False
            print(f"[Modelex] JWT verified, amount: {amount}")
            return True
        else:
            print(f"[Modelex] JWT amount not met: {amount} < {min_amount}")
            return False
    except Exception as e:
        print(f"[Modelex] JWT verification failed: {e}")
        return False

def verify_onchain(wallet_address: str, min_amount: float, phone_number: Optional[str] = None) -> bool:
    """
    Checks Solana blockchain for a recent transaction from the given wallet address
    with at least min_amount. Returns True if found, else False.
    Optionally accepts phone_number for future extensibility.
    """
    solana_rpc = "https://api.mainnet-beta.solana.com"
    client = SolanaClient(solana_rpc)
    try:
        # Get recent signatures for the address
        sigs_resp = client.get_signatures_for_address(PublicKey(wallet_address), limit=20)
        if not sigs_resp.value:
            return False
        for sig_info in sigs_resp.value:
            sig = sig_info.signature
            tx_resp = client.get_transaction(sig)
            if not tx_resp.value or not isinstance(tx_resp.value, dict):
                continue
            meta = tx_resp.value.get('meta', {})
            pre_balances = meta.get('preBalances', [])
            post_balances = meta.get('postBalances', [])
            if not pre_balances or not post_balances:
                continue
            # For demo: check if any balance decrease >= min_amount (in SOL)
            # 1 SOL = 1_000_000_000 lamports
            for pre, post in zip(pre_balances, post_balances):
                diff = (pre - post) / 1_000_000_000
                if diff >= min_amount:
                    print(f"[Modelex] On-chain payment found: {diff} SOL >= {min_amount} SOL, tx: {sig}")
                    return True
        return False
    except Exception as e:
        print(f"[Modelex] On-chain verification failed: {e}")
        return False
