import base64
import io
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

import qrcode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from authx import AuthX, AuthXConfig, TokenPayload
from fastapi import Depends, FastAPI, Query, Response
from starlette.middleware.cors import CORSMiddleware

from .dto import AccountCreateRequest, AccountDto, AccountUpdateRequest, AccountsResponse, CategoriesResponse, \
    CategoryCreateRequest, CategoryDto, CurrencyCode, \
    CurrencyCodes, \
    QRCodeResponse, \
    SessionStatusResponse, Transaction, \
    TransactionsResponse
from ..config import BOT_NAME, COOKIE_DOMAIN, DEV, EXPIRATION_TIME_SECONDS, SECRET
from ..core.models import Account, Category, Transaction as ModelTransaction, db
from ..core.service import clear_old_sessions, create_account, create_category, create_default_categories, \
    create_session, \
    delete_account_by_id_and_user_id, delete_category_by_id_and_user_id, get_category_by_id, \
    get_session, \
    get_transactions_for_period, \
    get_user_account_with_balance, get_user_accounts_with_balance, get_user_categories, update_account, update_category
from ..core.utils.currency_codes import CODES


async def clear_job():
    print("clearing sessions")
    await clear_old_sessions()


scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.aconnect()
    scheduler.add_job(clear_job, IntervalTrigger(minutes=5))
    scheduler.start()
    await clear_old_sessions()
    yield
    scheduler.shutdown()
    await db.aclose()
    await db.close_pool()


app = FastAPI(lifespan=lifespan)

if DEV:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
config = AuthXConfig(
    JWT_SECRET_KEY=SECRET,
    JWT_TOKEN_LOCATION=["cookies"],
    JWT_ACCESS_COOKIE_NAME="access_token",
    JWT_COOKIE_DOMAIN=COOKIE_DOMAIN,
    JWT_COOKIE_SAMESITE="strict",
    JWT_ACCESS_TOKEN_EXPIRES=EXPIRATION_TIME_SECONDS,
    JWT_COOKIE_CSRF_PROTECT=False
)
auth = AuthX(config)
auth.handle_errors(app)


@app.get("/api/transactions")
async def get_user_transactions(
        date_from: Annotated[date, Query(title="начальная дата", description="Начальная дата в формате yyyy-MM-dd")],
        date_to: Annotated[date, Query(title="конечная дата", description="Конечная дата в формате yyyy-MM-dd")],
        payload: TokenPayload = Depends(auth.access_token_required)
) -> \
        TransactionsResponse:
    transactions = await get_transactions_for_period(int(payload.sub), date_from, date_to)
    return TransactionsResponse(transactions=[convert_transaction_to_dto(tx) for tx in transactions])


@app.post("/api/create-session")
async def create_session_route() -> QRCodeResponse:
    session_id = await create_session()
    deeplink = f'https://t.me/{BOT_NAME}?start={session_id}'

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(deeplink)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    byte_io = io.BytesIO()
    img.save(byte_io, 'PNG')
    qr_code_base64 = base64.b64encode(byte_io.getvalue()).decode('utf-8')

    return QRCodeResponse(
        session_id=session_id,
        qr_code=f"data:image/png;base64,{qr_code_base64}"
    )


@app.get("/api/auth/{session_id}")
async def auth_user(session_id: str, response: Response) -> SessionStatusResponse:
    session = await get_session(session_id)
    if session.status == 'confirmed':
        token = auth.create_access_token(uid=str(session.user_id))
        auth.set_access_cookies(token, response, EXPIRATION_TIME_SECONDS)
    return SessionStatusResponse(status=session.status, session_id=session_id)


@app.get("/api/accounts")
async def get_user_accounts() -> AccountsResponse:
    accounts = await get_user_accounts_with_balance(433289417)
    return AccountsResponse(accounts={acc.id: convert_account_with_balance_to_dto(acc, am) for acc, am in accounts},
                            total=len(accounts))

@app.get("/api/accounts/account/{account_id}")
async def get_user_accounts(account_id: int) -> AccountDto:
    account, balance = await get_user_account_with_balance(433289417, account_id)
    return convert_account_with_balance_to_dto(account, balance)

@app.put("/api/accounts/account/{account_id}")
async def update_account_endpoint(account_id: int, update_request: AccountUpdateRequest) -> AccountDto:
    account, balance = await get_user_account_with_balance(433289417, account_id)
    account.name = update_request.name
    updated_account = await update_account(433289417, account, update_request.amount)
    return convert_account_with_balance_to_dto(updated_account, update_request.amount)

@app.delete("/api/accounts/account/{account_id}")
async def update_account_endpoint(account_id: int):
    await delete_account_by_id_and_user_id(433289417, account_id)

@app.post("/api/accounts/account")
async def create_account_endpoint(create_request: AccountCreateRequest) -> AccountDto:
    account = await create_account(433289417, create_request.name, create_request.amount, create_request.currency_code)
    return convert_account_with_balance_to_dto(account, create_request.amount)

@app.get("/api/currency/codes")
async def update_account_endpoint() -> CurrencyCodes:
    return CurrencyCodes(
        codes={code.get("CharCode"): CurrencyCode(
            num_code=int(code.get("NumCode", None)) if code.get("NumCode", None) is not None else None,
            char_code=code.get("CharCode")) for code in CODES.values()}
    )

@app.get("/api/categories")
async def get_user_categories_endpoint() -> CategoriesResponse:
    income, expense = await get_user_categories(433289417)
    if not income or not expense:
        await create_default_categories(433289417)
        income, expense = await get_user_categories(433289417)
    categories = {category.id : convert_category_to_dto(category) for category in income + expense}
    return CategoriesResponse(
        categories=categories
    )

@app.get("/api/categories/{category_id}")
async def get_user_category_endpoint(category_id: int) -> CategoryDto:
    category = await get_category_by_id(433289417, category_id)
    return convert_category_to_dto(category)

@app.post("/api/categories")
async def create_category_endpoint(create_request: CategoryCreateRequest) -> CategoryDto:
    category = await create_category(433289417, create_request.name, create_request.type)
    return convert_category_to_dto(category)

@app.put("/api/categories/{category_id}")
async def create_category_endpoint(category_id: int, create_request: CategoryCreateRequest) -> CategoryDto:
    category = await get_category_by_id(433289417, category_id)
    category.name = create_request.name
    category.type = create_request.type
    category = await update_category(category)
    return convert_category_to_dto(category)

@app.delete("/api/categories/{category_id}")
async def create_category_endpoint(category_id: int):
    await delete_category_by_id_and_user_id(433289417, category_id)

def convert_account_with_balance_to_dto(account: Account, balance: float):
    return AccountDto(
        id=account.id,
        user_id=account.user_id,
        name=account.name,
        amount=balance,
        currency_code=account.currency_code
    )


def convert_transaction_to_dto(transaction: ModelTransaction) -> Transaction:
    return Transaction(
        id=transaction.id,
        account=transaction.account.name,
        type=transaction.category.type,
        category=transaction.category.name,
        amount=transaction.amount * transaction.exchange_rate,
        description=transaction.description
    )

def convert_category_to_dto(category: Category) -> CategoryDto:
    return CategoryDto(
        id=category.id,
        name=category.name,
        type=category.type
    )