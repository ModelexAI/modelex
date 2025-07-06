from pydantic import BaseModel, Field
from typing import Optional, Dict

class PaymentReceipt(BaseModel):
    agent_name: str
    amount: float
    currency: str
    user_wallet: Optional[str] = None
    tx_hash: Optional[str] = None
    jwt_token: Optional[str] = None

class AgentRegistration(BaseModel):
    agent_name: str
    owner_pubkey: str
    price_per_call: float
    currency: str
    payment_endpoint: str

class UsageReport(BaseModel):
    agent_name: str
    amount: float
    currency: str
    metadata: Optional[Dict] = None

class PaymentRequiredResponse(BaseModel):
    error: str = "Payment required"
    price: float
    currency: str
    payment_endpoint: str = "https://pay.modelex.ai/pay"
    phone_required: bool = False

class PhoneVerificationResponse(BaseModel):
    error: str = "Phone verification required"
    verify_url: str = "https://modelex.ai/verify"

class RateLimitResponse(BaseModel):
    error: str = "Rate limit exceeded"
    retry_after: int
    requests_per_minute: int
