import base64
import io
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
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
    TransactionCreateRequest, TransactionsResponse
from ..config import BOT_NAME, COOKIE_DOMAIN, DEV, EXPIRATION_TIME_SECONDS, SECRET
from ..core.models import Account, Category, Transaction as ModelTransaction, db
from ..core.service import clear_old_sessions, create_account, create_category, create_default_categories, \
    create_session, \
    delete_account_by_id_and_user_id, delete_category_by_id_and_user_id, delete_transaction_by_id_and_user_id, \
    get_account_by_id, \
    get_category_by_id, \
    get_session, \
    get_transaction_by_id_and_user_id, get_transactions_for_period, \
    get_user_account_with_balance, get_user_accounts_with_balance, get_user_categories, save_transaction, \
    update_account, update_category, update_transaction
from ..core.service.exchage_rate_service import convert_to_rubles, get_currency_exchange_rate
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
    JWT_TOKEN_LOCATION=["cookies", "headers"],
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
    converted_transactions = [convert_transaction_to_dto(tx) for tx in transactions]
    return TransactionsResponse(transactions=converted_transactions, total_amount_rubles=sum([
        amount.amount_rubles for amount in converted_transactions if amount.amount_rubles is not None
    ]))

@app.get("/api/transactions/{transaction_id}")
async def get_transaction(
        transaction_id: int,
        payload: TokenPayload = Depends(auth.access_token_required)
) -> Transaction:
    transaction = await get_transaction_by_id_and_user_id(int(payload.sub), transaction_id)
    return convert_transaction_to_dto(transaction)

@app.post("/api/transactions")
async def create_transaction_endpoint(
        transaction_create: TransactionCreateRequest,
        payload: TokenPayload = Depends(auth.access_token_required)
) -> Transaction:
    account = await get_account_by_id(int(payload.sub), transaction_create.account_id)
    category = await get_category_by_id(int(payload.sub), transaction_create.category_id)
    transaction = convert_transaction_create_to_model(int(payload.sub), transaction_create, account, category,
                                                      await get_currency_exchange_rate(account.currency_code))
    transaction = await save_transaction(transaction)
    return convert_transaction_to_dto(transaction)

@app.put("/api/transactions/{transaction_id}")
async def update_transaction_endpoint(
        transaction_id: int,
        transaction_create: TransactionCreateRequest,
        payload: TokenPayload = Depends(auth.access_token_required)
) -> Transaction:
    account = await get_account_by_id(int(payload.sub), transaction_create.account_id)
    category = await get_category_by_id(int(payload.sub), transaction_create.category_id)
    transaction = await get_transaction_by_id_and_user_id(int(payload.sub), transaction_id)
    transaction.account = account
    transaction.category = category
    transaction.amount = transaction_create.amount
    transaction.description = transaction_create.description
    transaction.created_at = transaction_create.created_at
    transaction.updated_at = datetime.now(UTC)
    transaction.exchange_rate = await get_currency_exchange_rate(account.currency_code)

    transaction = await update_transaction(transaction)
    return convert_transaction_to_dto(transaction)

@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction_endpoint(
        transaction_id: int,
        payload: TokenPayload = Depends(auth.access_token_required)
):
    await delete_transaction_by_id_and_user_id(int(payload.sub), transaction_id)



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
async def get_user_accounts(
        payload: TokenPayload = Depends(auth.access_token_required)
) -> AccountsResponse:
    accounts = await get_user_accounts_with_balance(int(payload.sub))
    account_map = {acc.id: (await convert_account_with_balance_to_dto(acc, am)) for acc, am in accounts}
    return AccountsResponse(
        accounts=account_map,
        total=len(accounts),
        total_amount_rubles=sum(
            [account.amount_rubles for account in account_map.values() if account.amount_rubles is not None])
    )

@app.get("/api/accounts/account/{account_id}")
async def get_user_accounts(
        account_id: int,
        payload: TokenPayload = Depends(auth.access_token_required)
) -> AccountDto:
    account, balance = await get_user_account_with_balance(int(payload.sub), account_id)
    return await convert_account_with_balance_to_dto(account, balance)

@app.put("/api/accounts/account/{account_id}")
async def update_account_endpoint(
        account_id: int,
        update_request: AccountUpdateRequest,
        payload: TokenPayload = Depends(auth.access_token_required)
) -> AccountDto:
    account, balance = await get_user_account_with_balance(int(payload.sub), account_id)
    account.name = update_request.name
    updated_account = await update_account(int(payload.sub), account, update_request.amount)
    return await convert_account_with_balance_to_dto(updated_account, update_request.amount)

@app.delete("/api/accounts/account/{account_id}")
async def update_account_endpoint(
        account_id: int,
        payload: TokenPayload = Depends(auth.access_token_required)
):
    await delete_account_by_id_and_user_id(int(payload.sub), account_id)

@app.post("/api/accounts/account")
async def create_account_endpoint(
        create_request: AccountCreateRequest,
        payload: TokenPayload = Depends(auth.access_token_required)
) -> AccountDto:
    account = await create_account(int(payload.sub), create_request.name, create_request.amount, create_request.currency_code)
    return await convert_account_with_balance_to_dto(account, create_request.amount)

@app.get("/api/currency/codes")
async def update_account_endpoint() -> CurrencyCodes:
    return CurrencyCodes(
        codes={code.get("CharCode"): CurrencyCode(
            num_code=int(code.get("NumCode", None)) if code.get("NumCode", None) is not None else None,
            char_code=code.get("CharCode")) for code in CODES.values()}
    )

@app.get("/api/categories")
async def get_user_categories_endpoint(
        payload: TokenPayload = Depends(auth.access_token_required)
) -> CategoriesResponse:
    income, expense = await get_user_categories(int(payload.sub))
    if not income or not expense:
        await create_default_categories(int(payload.sub))
        income, expense = await get_user_categories(int(payload.sub))
    categories = {category.id : convert_category_to_dto(category) for category in income + expense}
    return CategoriesResponse(
        categories=categories
    )

@app.get("/api/categories/{category_id}")
async def get_user_category_endpoint(
        category_id: int,
        payload: TokenPayload = Depends(auth.access_token_required)
) -> CategoryDto:
    category = await get_category_by_id(int(payload.sub), category_id)
    return convert_category_to_dto(category)

@app.post("/api/categories")
async def create_category_endpoint(
        create_request: CategoryCreateRequest,
        payload: TokenPayload = Depends(auth.access_token_required)
) -> CategoryDto:
    category = await create_category(int(payload.sub), create_request.name, create_request.type)
    return convert_category_to_dto(category)

@app.put("/api/categories/{category_id}")
async def create_category_endpoint(
        category_id: int,
        create_request: CategoryCreateRequest,
        payload: TokenPayload = Depends(auth.access_token_required)
) -> CategoryDto:
    category = await get_category_by_id(int(payload.sub), category_id)
    category.name = create_request.name
    category.type = create_request.type
    category = await update_category(category)
    return convert_category_to_dto(category)

@app.delete("/api/categories/{category_id}")
async def create_category_endpoint(
        category_id: int,
        payload: TokenPayload = Depends(auth.access_token_required)
):
    await delete_category_by_id_and_user_id(int(payload.sub), category_id)

async def convert_account_with_balance_to_dto(account: Account, balance: float):
    return AccountDto(
        id=account.id,
        user_id=account.user_id,
        name=account.name,
        amount=balance,
        amount_rubles=await convert_to_rubles(balance, account.currency_code),
        currency_code=account.currency_code
    )


def convert_transaction_to_dto(transaction: ModelTransaction) -> Transaction:
    return Transaction(
        id=transaction.id,
        account=transaction.account.name,
        account_id=transaction.account.id,
        type=transaction.category.type,
        category=transaction.category.name,
        category_id=transaction.category.id,
        amount=transaction.amount,
        amount_rubles=transaction.amount * transaction.exchange_rate,
        description=transaction.description,
        currency_code=transaction.account.currency_code,
        created_at=transaction.created_at
    )

def convert_category_to_dto(category: Category) -> CategoryDto:
    return CategoryDto(
        id=category.id,
        name=category.name,
        type=category.type
    )


def convert_transaction_create_to_model(user_id: int, transaction_create: TransactionCreateRequest, account: Account,
                                        category: Category, exchange_rate: float) -> ModelTransaction:
    return ModelTransaction(
        user_id=user_id,
        account=account,
        category=category,
        amount=transaction_create.amount,
        description=transaction_create.description,
        created_at=datetime.now(UTC) if transaction_create.created_at is None else transaction_create.created_at,
        updated_at=datetime.now(UTC),
        exchange_rate=exchange_rate
    )


if __name__ == "__main__":
    print(auth.create_access_token(uid="433289417"))