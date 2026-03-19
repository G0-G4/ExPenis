from pydantic import BaseModel, field_validator
from typing import Literal

from src.expenis.core.service import SessionStatus
from src.expenis.core.utils.currency_codes import CODES


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


class AccountDto(BaseModel):
    id: int
    user_id: int
    name: str
    amount: float
    currency_code: str

class AccountsResponse(BaseModel):
    accounts: dict[int, AccountDto]
    total: int

class AccountUpdateRequest(BaseModel):
    id: int
    name: str
    amount: float

class AccountCreateRequest(BaseModel):
    name: str
    amount: float
    currency_code: str

    @field_validator("currency_code")
    @classmethod
    def name_must_contain_space(cls, v: str) -> str:
        if v not in CODES:
            raise ValueError("Unknown currency code")
        return v


class CurrencyCode(BaseModel):
    num_code: int | None
    char_code: str

class CurrencyCodes(BaseModel):
    codes: dict[str, CurrencyCode]