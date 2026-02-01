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

from .dto import QRCodeResponse, SessionStatusResponse, Transaction, TransactionsResponse
from ..config import BOT_NAME, COOKIE_DOMAIN, DEV, EXPIRATION_TIME_SECONDS, SECRET
from ..core.models import Transaction as ModelTransaction, db
from ..core.service import clear_old_sessions, create_session, get_session, get_transactions_for_period


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


def convert_transaction_to_dto(transaction: ModelTransaction) -> Transaction:
    return Transaction(
        id=transaction.id,
        account=transaction.account.name,
        type=transaction.category.type,
        category=transaction.category.name,
        amount=transaction.amount
    )
