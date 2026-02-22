from pydantic import BaseModel
from typing import Literal

from src.expenis.core.service import SessionStatus


class Transaction(BaseModel):
    id: int
    account: str
    type: Literal["income", "expense"]
    category: str
    amount: float
    description: str | None

class TransactionsResponse(BaseModel):
    transactions: list[Transaction]


class SessionStatusResponse(BaseModel):
    session_id: str
    status: SessionStatus

class QRCodeResponse(BaseModel):
    session_id: str
    qr_code: str  # base64 encoded image