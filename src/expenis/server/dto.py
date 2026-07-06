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
    tags: list[str]
    currency_code: str
    created_at: datetime

class TransactionCreateRequest(BaseModel):
    account_id: int
    category_id: int
    amount: float
    description: str | None
    tags: list[str] | None = None
    created_at: datetime | None


class TransactionsResponse(BaseModel):
    transactions: list[Transaction]
    total_amount_rubles: float


class UserTagsResponse(BaseModel):
    tags: list[str]


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


class DeleteAccountResponse(BaseModel):
    delete_type: Literal["soft", "hard"]


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


class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("username must not be empty")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("password must not be empty")
        return v

class RegisterRequest(LoginRequest):
    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("password must be at least 6 characters")
        return v


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int

class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int

class LogoutResponse(BaseModel):
    detail: str = "logged out"


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("old_password")
    @classmethod
    def old_password_non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("old_password must not be empty")
        return v

    @field_validator("new_password")
    @classmethod
    def new_password_non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("new_password must not be empty")
        return v

    @field_validator("new_password")
    @classmethod
    def new_password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("password must be at least 6 characters")
        return v


class MeResponse(BaseModel):
    id: int
    username: str | None
    telegram_id: int | None
