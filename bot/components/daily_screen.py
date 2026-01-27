import os
from datetime import UTC, date, datetime, timedelta
from typing import ClassVar, Sequence

from telegram import InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from tuican import get_user_id
from tuican.components import Button, Component, Hline, Screen, ScreenGroup

from bot.components.transaction_screen import TransactionCreate, TransactionEdit
from core.helpers import format_amount
from core.models.transaction import Transaction
from core.service.transaction_service import get_transactions_for_period


def get_transaction_label(transaction: Transaction)-> str:
    emoji = "🟢" if transaction.category.type == "income" else "🔴"
    formatted_amount = format_amount(transaction.amount)
    return f"{emoji} {formatted_amount:>10} ({transaction.category.name})"


class DailyScreen(Screen):
    def __init__(self, group: ScreenGroup):
        self.left = Button(text="◀", on_change=self.left_handler)
        self.today = Button("today", on_change=self.today_handler)
        self.hline = Hline()
        self.right = Button(text="▶", on_change=self.right_handler)
        self.new_transaction = Button(text="➕ new", on_change=self.new_transaction_handler)
        self.transactions = None
        self.transactions_buttons = []
        self.selected_date = datetime.now(UTC).date()
        self.group = group
        super().__init__([self.left, self.today, self.right, self.new_transaction], message=self.get_message())


    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[Sequence[InlineKeyboardButton]]:
        await self.add_transactions(get_user_id(update))
        return ([[b.render(update, context)] for b in self.transactions_buttons] +
                [
                    [self.hline.render(update, context)],
                    [self.new_transaction.render(update, context)],
                    [self.left.render(update, context), self.today.render(update, context),
                     self.right.render(update, context)]
                ])

    def left_handler(self, *args, **kwargs):
        self.selected_date -= timedelta(days=1)
        self.remove_transactions()
        self.message = self.get_message()

    def right_handler(self, *args, **kwargs):
        self.selected_date += timedelta(days=1)
        self.remove_transactions()
        self.message = self.get_message()

    def today_handler(self, *args, **kwargs):
        self.selected_date = datetime.now(UTC).date()
        self.remove_transactions()
        self.message = self.get_message()

    async def new_transaction_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                callback_data: str | None, cmp: Component):
        screen = TransactionCreate(self.group)
        self.remove_transactions()
        await self.group.go_to_screen(update, context, screen)

    async def edit_transaction_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                      callback_data: str | None, cmp: Component):
        screen = TransactionEdit(int(cmp.component_id), self.group)
        self.remove_transactions()
        await self.group.go_to_screen(update, context, screen)


    def get_message(self) -> str:
        return f"Transaction: {self.selected_date}"

    async def add_transactions(self, user_id: int):
        if self.transactions is None:
            self.transactions = await get_transactions_for_period(user_id, self.selected_date, self.selected_date)
            for transaction in self.transactions:
                label = get_transaction_label(transaction)
                b = Button(text=label, on_change=self.edit_transaction_handler, component_id=str(transaction.id))
                self.add_component(b)
                self.transactions_buttons.append(b)

    def remove_transactions(self):
        for button in self.transactions_buttons:
            self.delete_component(button)
        self.transactions_buttons = []
        self.transactions = None

class MainScreen(ScreenGroup):
    description: ClassVar[str] = "траты по дням"
    def __init__(self):
        self.main = DailyScreen(self)
        super().__init__(self.main)

