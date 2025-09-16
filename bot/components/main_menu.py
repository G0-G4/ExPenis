from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.components.component import UiComponent
from bot.messages import *
from bot.keyboards import get_main_menu_keyboard
from core.service.transaction_service import get_todays_totals, get_todays_transactions
from core.helpers import format_amount


class MainMenu(UiComponent):
    def __init__(self, component_id: str = None, on_change: callable = None):
        super().__init__(component_id, on_change)

    async def init(self, update, context, user_id: int = None):
        """Initialize with consistent signature - user_id can come from context or parameter"""
        if user_id is None:
            user_id = context.user_data.get('user_id') or context._user_id
        await self.fetch_data(user_id, context)
        self.initiated = True

    async def clear_state(self, update, context):
        """Clear component state"""
        self.initiated = False
        # Clear stored data from context
        context.user_data.pop('todays_transactions', None)
        context.user_data.pop('totals', None)
        context.user_data.pop('total_income', None)
        context.user_data.pop('total_expense', None)
        context.user_data.pop('net_total', None)

    async def fetch_data(self, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        todays_transactions = await get_todays_transactions(user_id)
        totals = await get_todays_totals(user_id)
        
        # Store user-specific data in context.user_data
        context.user_data['todays_transactions'] = todays_transactions
        context.user_data['totals'] = totals
        context.user_data['total_income'] = totals["total_income"]
        context.user_data['total_expense'] = totals["total_expense"]
        context.user_data['net_total'] = totals["net_total"]

    def render(self, update, context):
        keyboard = []
        todays_transactions = context.user_data.get('todays_transactions', [])
        
        for transaction in todays_transactions:
            emoji = "🟢" if transaction.type == "income" else "🔴"
            formatted_amount = format_amount(transaction.amount)
            button_text = f"{emoji} {formatted_amount:>10} ({transaction.category})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_transaction_{transaction.id}")])
        
        # Add separator if there are transactions
        if todays_transactions:
            keyboard.append([InlineKeyboardButton("───────────────", callback_data="separator")])
        
        # Add main menu button
        keyboard.extend(get_main_menu_keyboard())
        
        return keyboard

    async def get_message(self, update, context):
        """Get message text for this component with consistent signature"""
        # Get user-specific data
        total_income = context.user_data.get('total_income', 0)
        total_expense = context.user_data.get('total_expense', 0)
        net_total = context.user_data.get('net_total', 0)
        todays_transactions = context.user_data.get('todays_transactions', [])
        
        # Build message text with totals
        totals_text = f"\n\n{TOTAL_INCOME_MESSAGE.format(total_income=format_amount(total_income))}\n"
        totals_text += f"{TOTAL_EXPENSE_MESSAGE.format(total_expense=format_amount(total_expense))}\n"
        if net_total >= 0:
            totals_text += f"{NET_TOTAL_MESSAGE.format(net_total=f'+{format_amount(net_total)}')}"
        else:
            totals_text += f"{NET_TOTAL_MESSAGE.format(net_total=f'-{format_amount(abs(net_total))}')}"

        message_text = WELCOME_MESSAGE
        if todays_transactions:
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