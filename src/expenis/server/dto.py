from pydantic import BaseModel
from typing import Literal

from src.expenis.core.service import SessionStatus


class Transaction(BaseModel):
    id: int
    account: str
    type: Literal["income", "expense"]
    category: str
    amount: float

class TransactionsResponse(BaseModel):
    transactions: list[Transaction]


class SessionCreateResponse(BaseModel):
   session_id: str


class SessionStatusResponse(BaseModel):
    session_id: str
    status: SessionStatus