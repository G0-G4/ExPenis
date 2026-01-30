from pydantic import BaseModel
from typing import Literal

class Transaction(BaseModel):
    account: str
    type: Literal["income", "expense"]
    category: str
    amount: float

class TransactionsResponse(BaseModel):
    transactions: list[Transaction]