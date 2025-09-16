from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.components.component import UiComponent
from bot.messages import *
from bot.keyboards import get_main_menu_keyboard
from core.helpers import format_amount


class MainMenu(UiComponent):
    def __init__(self, todays_transactions=None, totals=None, component_id: str = None, on_change: callable = None):
        super().__init__(component_id, on_change)
        self.todays_transactions = todays_transactions or []
        self.totals = totals or {"total_income": 0, "total_expense": 0, "net_total": 0}
        self.initiated = True

    def update_data(self, todays_transactions=None, totals=None):
        """Update component data"""
        if todays_transactions is not None:
            self.todays_transactions = todays_transactions
        if totals is not None:
            self.totals = totals
        self.initiated = True

    def render(self, update, context):
        keyboard = []
        
        for transaction in self.todays_transactions:
            emoji = "🟢" if transaction.type == "income" else "🔴"
            formatted_amount = format_amount(transaction.amount)
            button_text = f"{emoji} {formatted_amount:>10} ({transaction.category})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_transaction_{transaction.id}")])
        
        # Add separator if there are transactions
        if self.todays_transactions:
            keyboard.append([InlineKeyboardButton("───────────────", callback_data="separator")])
        
        # Add main menu button
        keyboard.extend(get_main_menu_keyboard())
        
        return keyboard

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
        if self.todays_transactions:
            message_text = f"{WELCOME_MESSAGE}\n\n{TODAYS_TRANSACTIONS_MESSAGE}{totals_text}"
        else:
            message_text = f"{WELCOME_MESSAGE}\n\n{NO_TRANSACTIONS_MESSAGE}{totals_text}"
        return message_text

    async def handle_callback(self, update, context, callback_data: str) -> bool:
        if callback_data.startswith("view_transaction_"):
            # Handle transaction view - could trigger showing transaction details
            await self.call_on_change(update, context)
            return True
        elif callback_data == "separator":
            # Ignore separator clicks
            return True
        return False