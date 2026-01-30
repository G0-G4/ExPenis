from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import FastAPI, Query
from starlette.middleware.cors import CORSMiddleware

from src.expenis.server.dto import Transaction, TransactionsResponse
from ..core.models import Transaction as ModelTransaction, db
from ..core.service import get_transactions_for_period


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

@app.get("/transactions")
async def get_user_transactions(
        date_from: Annotated[date, Query(title="начальная дата", description="Начальная дата в формате yyyy-MM-dd")],
        date_to: Annotated[date, Query(title="конечная дата", description="Конечная дата в формате yyyy-MM-dd")]) -> \
        TransactionsResponse:
    transactions = await get_transactions_for_period(433289417, date_from, date_to)
    return TransactionsResponse(transactions=[convert_transaction_to_dto(tx) for tx in transactions])


def convert_transaction_to_dto(transaction: ModelTransaction) -> Transaction:
    return Transaction(
        id=transaction.id,
        account=transaction.account.name,
        type=transaction.category.type,
        category=transaction.category.name,
        amount=transaction.amount
    )
