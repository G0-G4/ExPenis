from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.components.component import UiComponent
from bot.components.navigation_arrows import NavigationArrows
from bot.messages import *
from bot.keyboards import get_main_menu_keyboard
from core.helpers import format_amount
from datetime import date


class MainMenu(UiComponent):
    def __init__(self, transactions=None, totals=None, component_id: str = None, on_change: callable = None, selected_date: date = None):
        super().__init__(component_id, on_change)
        if selected_date is None:
            self.selected_date = date.today()
        self.transactions = transactions or []
        self.totals = totals or {"total_income": 0, "total_expense": 0, "net_total": 0}
        self.navigation = NavigationArrows(self.selected_date, on_change=self._navigation_change)
        self.initiated = True

    def update_data(self, transactions=None, totals=None):
        """Update component data"""
        if transactions is not None:
            self.transactions = transactions
        if totals is not None:
            self.totals = totals
        self.initiated = True

    def render(self, update, context):
        keyboard = []
        
        for transaction in self.transactions:
            emoji = "🟢" if transaction.type == "income" else "🔴"
            formatted_amount = format_amount(transaction.amount)
            button_text = f"{emoji} {formatted_amount:>10} ({transaction.category})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_transaction_{transaction.id}")])
        
        # Add separator if there are transactions
        if self.transactions:
            keyboard.append([InlineKeyboardButton("───────────────", callback_data="separator")])
        
        # Add main menu button
        keyboard.append([InlineKeyboardButton("➕ Enter Transaction", callback_data='enter_transaction')])
        keyboard.extend(self.navigation.render(update, context))

        return keyboard

    def get_selected_period(self) -> tuple[date, date]:
        return self.navigation.get_current_period()

    def get_message(self):
        """Get message text for this component"""
        total_income = self.totals.get('total_income', 0)
        total_expense = self.totals.get('total_expense', 0) 
        net_total = self.totals.get('net_total', 0)
        
        # Build message text with totals
        totals_text = f"\n\n{TOTAL_INCOME_MESSAGE.format(total_income=format_amount(total_income))}\n"
        totals_text += f"{TOTAL_EXPENSE_MESSAGE.format(total_expense=format_amount(total_expense))}\n"
        if net_total >= 0:
            totals_text += f"{NET_TOTAL_MESSAGE.format(net_total=f'+{format_amount(net_total)}')}"
        else:
            totals_text += f"{NET_TOTAL_MESSAGE.format(net_total=f'-{format_amount(abs(net_total))}')}"

        message_text = WELCOME_MESSAGE
        if self.transactions:
            message_text = f"{WELCOME_MESSAGE}\n\n{TODAYS_TRANSACTIONS_MESSAGE}{totals_text}"
        else:
            message_text = f"{WELCOME_MESSAGE}\n\n{NO_TRANSACTIONS_MESSAGE}{totals_text}"
        return message_text

    async def _navigation_change(self, nav: NavigationArrows, update, context):
        await self.call_on_change(update, context)

    async def handle_callback(self, update, context, callback_data: str) -> bool:
        if callback_data.startswith("nav"):
            return await self.navigation.handle_callback(update, context, callback_data)
        return False