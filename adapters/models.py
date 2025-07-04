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
