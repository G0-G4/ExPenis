from datetime import UTC, date, datetime, timedelta
from typing import ClassVar, Sequence

from telegram import InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from tuican import get_user_id
from tuican.components import Button, Component, Hline, Screen, ScreenGroup

from ..service.transaction_service import calculate_transaction_stats, get_transaction_label
from ...bot.components.transaction_screen import TransactionCreate, TransactionEdit
from ...core.helpers import format_amount
from ...core.models import Transaction
from ...core.service import confirm_session
from ...core.service.transaction_service import get_transactions_for_period
from ...server.application import auth


def get_message(transactions: list[Transaction], dt: date) -> str:
    income, expense, total = calculate_transaction_stats(transactions)
    max_length = max(len(format_amount(income)), len(format_amount(expense)), len(format_amount(total)))
    padding_width = max_length + 2
    separator = (10 + padding_width) * "─"
    return f"""
<code>{dt}</code>
<code>🟢 Доходы  {f'{format_amount(income)} ₽':>{padding_width}}</code>
<code>🔴 Расходы {f'{format_amount(expense)} ₽':>{padding_width}}</code>
<code>{separator}</code>
<code>📊 Итого   {f'{format_amount(total)} ₽':>{padding_width}}</code>
"""


class CommandHandlerScreen(Screen):
    description: ClassVar[str] = "CommandHandlerScreen"

    def __init__(self):
        super().__init__([])

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        return [[]]

    async def command_handler(self, args: list[str], update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(args) == 1 and args[0] == 'mobile_token':
            token = auth.create_access_token(uid=str(get_user_id(update)))
            chat_id = update.effective_chat.id
            await context.bot.send_message(chat_id=chat_id, text=str(token))


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
        super().__init__([self.left, self.today, self.right, self.new_transaction])

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
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

    def right_handler(self, *args, **kwargs):
        self.selected_date += timedelta(days=1)
        self.remove_transactions()

    def today_handler(self, *args, **kwargs):
        self.selected_date = datetime.now(UTC).date()
        self.remove_transactions()

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

    async def add_transactions(self, user_id: int):
        if self.transactions is None:
            self.transactions = await get_transactions_for_period(user_id, self.selected_date, self.selected_date)
            self.message = get_message(self.transactions, self.selected_date)
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

    async def command_handler(self, args: list[str], update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(args) == 2:
            screen = ConfirmSessionScreen(args[1], self.group)
            await self.group.go_to_screen(update, context, screen)


class ConfirmSessionScreen(Screen):
    def __init__(self, session_id: str, group: ScreenGroup):
        self.group = group
        self.session_id = session_id
        self.confirm = Button("✅ подтвердить вход", on_change=self.handle_confirm)
        self.cancel = Button("❌ запретить", on_change=self.handel_cancel)
        super().__init__([self.confirm, self.cancel], message="подтвердить вход?")

    async def handle_confirm(self, update, context, callback_data, component):
        await confirm_session(get_user_id(update), self.session_id)
        await self.send_message(update, context, f"входи подтвержден, подождите немного")
        await self.group.go_home(update, context)

    async def handel_cancel(self, update, context, callback_data, component):
        await self.group.go_home(update, context)

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        return [[self.confirm.render(update, context), self.cancel.render(update, context)]]


class MainScreen(ScreenGroup):
    description: ClassVar[str] = "траты по дням"

    def __init__(self):
        self.main = DailyScreen(self)
        super().__init__(self.main)
