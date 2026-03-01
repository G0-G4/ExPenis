from src.expenis.core.helpers import format_amount
from src.expenis.core.models import Account
from src.expenis.core.service.exchage_rate_service import get_currency_exchange_rate


def get_account_label(account: Account, amount: float):
    if account.currency_code == "RUB":
        f"{account.name} {format_amount(amount)} ₽"
    return f"{account.name} {format_amount(amount)} {account.currency_code}"

async def get_account_label_in_rubles(account: Account, amount: float):
    if account.currency_code != 'RUB':
        amount = amount * await get_currency_exchange_rate(account.currency_code)
    return f"{format_amount(amount)} ₽"

async def get_total_sum_in_rubles(accounts_with_balances: list[tuple[Account, float]]) -> float:
    amount = 0
    for account, balance in accounts_with_balances:
        amount += balance * await get_currency_exchange_rate(account.currency_code)
    return amount
