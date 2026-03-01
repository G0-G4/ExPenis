from src.expenis.core.helpers import format_amount
from src.expenis.core.models import Transaction


def get_transaction_label(transaction: Transaction)-> str:
    emoji = "🟢" if transaction.category.type == "income" else "🔴"
    formatted_amount_rubles = format_amount(transaction.amount * transaction.exchange_rate)
    formatted_amount = format_amount(transaction.amount)
    comment =  transaction.description or ""
    if transaction.account.currency_code != "RUB":
        return f"{emoji} {formatted_amount} {transaction.account.currency_code} ≈ {formatted_amount_rubles} ₽ ({transaction.category.name}) {comment}"
    return f"{emoji} {formatted_amount_rubles} ₽ ({transaction.category.name}) {comment}"

def calculate_transaction_stats(transactions: list[Transaction]) -> tuple[float, float, float]:
    income = 0.0
    expense = 0.0
    total = 0.0
    for transaction in transactions:
        if transaction.category.type == 'income':
            income += transaction.amount * transaction.exchange_rate
        if transaction.category.type == 'expense':
            expense += transaction.amount * transaction.exchange_rate
    total = income - expense
    return income, expense, total
