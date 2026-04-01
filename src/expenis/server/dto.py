from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

from src.expenis.core.service import SessionStatus
from src.expenis.core.utils.currency_codes import CODES


class Transaction(BaseModel):
    id: int
    account: str
    account_id: int
    type: Literal["income", "expense"]
    category: str
    category_id: int
    amount: float
    amount_rubles: float
    description: str | None
    currency_code: str
    created_at: datetime

class TransactionCreateRequest(BaseModel):
    account_id: int
    category_id: int
    amount: float
    description: str | None
    created_at: datetime | None


class TransactionsResponse(BaseModel):
    transactions: list[Transaction]
    total_amount_rubles: float


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
    amount_rubles: float
    currency_code: str


class AccountsResponse(BaseModel):
    accounts: dict[int, AccountDto]
    total: int
    total_amount_rubles: float


class AccountUpdateRequest(BaseModel):
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


class CategoryDto(BaseModel):
    id: int
    type: Literal['income', 'expense']
    name: str


class CategoriesResponse(BaseModel):
    categories: dict[int, CategoryDto]

class CategoryCreateRequest(BaseModel):
    type: Literal['income', 'expense']
    name: str
