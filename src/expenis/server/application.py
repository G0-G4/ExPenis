from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Annotated

from authx import AuthX, AuthXConfig, TokenPayload
import io
import qrcode
from fastapi import Depends, FastAPI, Query, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware

from .dto import SessionCreateResponse, SessionStatusResponse, Transaction, TransactionsResponse
from ..core.models import Transaction as ModelTransaction, db
from ..core.service import create_session, get_session, get_transactions_for_period


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.aconnect()
    yield
    await db.aclose()
    await db.close_pool()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
EXPIRATION_TIME = timedelta(days=1)
config = AuthXConfig(
    JWT_SECRET_KEY="SECRET",  # TODO
    JWT_TOKEN_LOCATION=["cookies"],
    JWT_ACCESS_COOKIE_NAME="access_token",
    JWT_COOKIE_DOMAIN="localhost",  # TODO
    JWT_COOKIE_SAMESITE="strict",
    JWT_ACCESS_TOKEN_EXPIRES=EXPIRATION_TIME,
    JWT_COOKIE_CSRF_PROTECT=False
)
auth = AuthX(config)
auth.handle_errors(app)


@app.get("/transactions")
async def get_user_transactions(
        date_from: Annotated[date, Query(title="начальная дата", description="Начальная дата в формате yyyy-MM-dd")],
        date_to: Annotated[date, Query(title="конечная дата", description="Конечная дата в формате yyyy-MM-dd")],
        payload: TokenPayload = Depends(auth.access_token_required)
) -> \
        TransactionsResponse:
    transactions = await get_transactions_for_period(int(payload.sub), date_from, date_to)
    return TransactionsResponse(transactions=[convert_transaction_to_dto(tx) for tx in transactions])


@app.post("/create-session")
async def create_session_route() -> StreamingResponse:
    session_id = await create_session()
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(session_id)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    byte_io = io.BytesIO()
    img.save(byte_io, 'PNG')
    byte_io.seek(0)
    
    return StreamingResponse(byte_io, media_type="image/png")


@app.get("/auth/{session_id}")
async def auth_user(session_id: str, response: Response) -> SessionStatusResponse:
    session = await get_session(session_id)
    if session.status == 'confirmed':
        token = auth.create_access_token(uid=str(session.user_id))
        auth.set_access_cookies(token, response, int(EXPIRATION_TIME.total_seconds()))
    return SessionStatusResponse(status=session.status, session_id=session_id)


def convert_transaction_to_dto(transaction: ModelTransaction) -> Transaction:
    return Transaction(
        id=transaction.id,
        account=transaction.account.name,
        type=transaction.category.type,
        category=transaction.category.name,
        amount=transaction.amount
    )
