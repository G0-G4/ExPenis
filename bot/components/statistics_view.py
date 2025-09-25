from datetime import date
from typing import Literal, Optional
from telegram import InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from decimal import Decimal

from bot.components.component import UiComponent
from bot.components.check_box import CheckBox, ExclusiveCheckBoxGroup
from bot.components.navigation_arrows import NavigationArrows
from core.helpers import format_amount, format_percentage, calculate_period_dates, format_date
from core.service.transaction_service import get_transactions_for_category

PeriodType = Literal['day', 'week', 'month', 'year']

class StatisticsView(UiComponent):
    def __init__(self, 
                 income_data: dict = None, 
                 expense_data: dict = None,
                 period_type: PeriodType = 'month',
                 component_id: str = None,
                 on_change: callable = None,
                 on_category_select = None):
        super().__init__(component_id, on_change)
        self.showing_transactions = False
        self.current_category = None
        self.current_type = None
        self.transactions = []
        
        self.income_data = income_data or {}
        self.expense_data = expense_data or {}
        
        self.income_checkbox = CheckBox(
            "Income",
            selected=True,
        )
        self.expense_checkbox = CheckBox(
            "Expense", 
            selected=True,
        )
        
        # Navigation
        self.navigation = NavigationArrows(
            date.today(),
            period_type=period_type,
            on_change=self._on_period_change
        )
        
        # Period quick select buttons
        self.period_buttons = [
            ("Today", "day"),
            ("This Week", "week"), 
            ("This Month", "month"),
            ("This Year", "year")
        ]
        
        self.initiated = True

    def update_data(self, income_data=None, expense_data=None, transactions=None):
        """Update statistics data"""
        if income_data is not None:
            self.income_data = income_data
        if expense_data is not None:
            self.expense_data = expense_data
        if transactions is not None:
            self.transactions = transactions
        self.initiated = True

    def render(self, update, context):
        """Render the statistics UI"""
        if self.showing_transactions:
            return self._render_transactions_list()
        return self._render_statistics_view(update, context)

    def _render_transactions_list(self):
        """Render list of transactions for selected category"""
        keyboard = []
        

        # Transactions list
        for transaction in self.transactions:
            keyboard.append([InlineKeyboardButton(
                f"{format_amount(transaction.amount)} - {format_date(transaction.created_at.date())}",
                callback_data=f"view_transaction_{transaction.id}"
            )])

        # back button
        keyboard.append([InlineKeyboardButton(
            f"⬅️ Back to stats",
            callback_data="stats_back_to_view"
        )])

        return keyboard

    def _render_statistics_view(self, update, context):
        """Render the normal statistics view"""
        keyboard = []
        
        # Type selector
        keyboard.append([
            self.income_checkbox.render(update, context),
            self.expense_checkbox.render(update, context)
        ])
        
        # Period quick select
        period_row = []
        for text, period in self.period_buttons:
            period_row.append(InlineKeyboardButton(
                text,
                callback_data=f"stats_period_{period}"
            ))
        keyboard.append(period_row)
        
        # Navigation controls
        keyboard.extend(self.navigation.render(update, context))
        
        # Income statistics
        if self.income_checkbox.selected and self.income_data:
            keyboard.append([InlineKeyboardButton(
                "💰 INCOME STATISTICS",
                callback_data="stats_header_income"
            )])
            for category, data in self.income_data.items():
                keyboard.append([InlineKeyboardButton(
                    f"{category}: {format_amount(data['amount'])} ({format_percentage(data['percentage'])})",
                    callback_data=f"stats_detail_income_{category}"
                )])
            keyboard.append([InlineKeyboardButton("───────────────", callback_data="separator")])
        
        # Expense statistics
        if self.expense_checkbox.selected and self.expense_data:
            keyboard.append([InlineKeyboardButton(
                "🛒 EXPENSE STATISTICS",
                callback_data="stats_header_expense"
            )])
            for category, data in self.expense_data.items():
                keyboard.append([InlineKeyboardButton(
                    f"{category}: {format_amount(data['amount'])} ({format_percentage(data['percentage'])})",
                    callback_data=f"stats_detail_expense_{category}"
                )])
                
        return keyboard

    def get_message(self):
        """Get appropriate message based on current view"""
        if self.showing_transactions:
            start_date, end_date = self.navigation.get_current_period()
            return f"📋 Transactions for {self.current_category} ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
        return f"📊 Statistics for {self.navigation.get_current_period()[0].strftime('%Y-%m-%d')} to {self.navigation.get_current_period()[1].strftime('%Y-%m-%d')}"

    async def _on_type_change(self, group, update, context):
        """Handle type (income/expense) selection changes"""
        await self.call_on_change(update, context)

    async def _on_period_change(self, nav, update, context):
        """Handle period navigation changes"""
        await self.call_on_change(update, context)

    async def handle_callback(self, update, context, callback_data: str) -> bool:
        """Handle all button callbacks"""
        # Handle back from transactions list
        if callback_data == "stats_back_to_view":
            self.showing_transactions = False
            await self.call_on_change(update, context)
            return True
            
        # Handle category detail clicks
        if callback_data.startswith("stats_detail_"):
            parts = callback_data.split("_")
            self.current_type = parts[2]  # income/expense
            self.current_category = "_".join(parts[3:])  # handle categories with spaces
            self.showing_transactions = True
            await self.call_on_change(update, context)
            return True
            
        # Type selection
        if await self.income_checkbox.handle_callback(update, context, callback_data):
            return True
        if await self.expense_checkbox.handle_callback(update, context, callback_data):
            return True

        # Period quick selection
        if callback_data.startswith("stats_period_"):
            period = callback_data.split("_")[2]
            self.navigation.update_data(period_type=period, offset=0)
            await self.call_on_change(update, context)
            return True
            
        # Navigation arrows
        if await self.navigation.handle_callback(update, context, callback_data):
            return True
            
        return False
