from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest
from typing import Optional

from bot.messages import *
from bot.bot_config import *
from bot.screens.check_box import CheckBox, CheckBoxGroup, Panel
from core.service.account_service import get_user_accounts, calculate_account_balance
from core.service.category_service import ensure_user_has_categories
from core.helpers import format_amount

class TransactionEditScreen:
    def __init__(self, application: Application):
        self.income_cats = []
        self.expense_cats = []
        self.accounts = []
        self.account_id: Optional[int] = None
        self.transaction_type = 'expense'
        self.category: Optional[str] = None
        self.current_panel = Panel()
        
        application.add_handler(CallbackQueryHandler(
            self.enter_transaction_handler, 
            pattern='^enter_transaction$'
        ))
        application.add_handler(CallbackQueryHandler(
            self.handle_callback,
            pattern='^cb_|^back$'
        ))

    async def enter_transaction_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.callback_query.from_user.id
        await self.fetch_data(user_id)
        
        if not self.accounts:
            return await self.display_on(
                update, 
                NO_ACCOUNTS_MESSAGE, 
                InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]])
            )
            
        await self.display_on(
            update,
            ACCOUNT_SELECTION_MESSAGE,
            await self.create_transaction_panel(user_id)
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        
        if query.data == 'back':
            # Handle back button
            return await self.display_on(
                update,
                MAIN_MENU_MESSAGE,
                get_main_menu_keyboard()
            )
            
        # Let the panel handle component callbacks
        if self.current_panel.handle_callback(query.data):
            await self.display_on(
                update,
                ACCOUNT_SELECTION_MESSAGE,
                await self.create_transaction_panel(user_id)
            )

    async def create_transaction_panel(self, user_id: int) -> Panel:
        panel = Panel()
        
        # Account selection
        account_group = CheckBoxGroup("accounts", 
                                    on_change=lambda cb: setattr(self, 'account_id', int(cb.component_id)))
        for account in self.accounts:
            balance = await calculate_account_balance(account.id, user_id)
            cb = CheckBox(
                f"{account.name} ({format_amount(balance)})",
                account.id == self.account_id,
                component_id=str(account.id)
            )
            account_group.add(cb)
            panel.add(cb)
        
        # Transaction type selection
        type_group = CheckBoxGroup("transaction_type", 
                                 on_change=lambda cb: self._handle_type_change(cb))
        income_cb = CheckBox(
            "🟢 Income (+)",
            self.transaction_type == 'income',
            component_id="income"
        )
        expense_cb = CheckBox(
            "🔴 Expense (-)", 
            self.transaction_type == 'expense',
            component_id="expense"
        )
        type_group.add(income_cb)
        type_group.add(expense_cb)
        panel.add(Panel([income_cb, expense_cb]))
        
        # Category selection
        if self.transaction_type and self.account_id:
            cats = self.expense_cats if self.transaction_type == 'expense' else self.income_cats
            msg = EXPENSE_CATEGORY_MESSAGE if self.transaction_type == 'expense' else INCOME_CATEGORY_MESSAGE
            
            category_group = CheckBoxGroup("categories",
                                         on_change=lambda cb: setattr(self, 'category', cb.text))
            for category in cats:
                cb = CheckBox(
                    category.name,
                    category.name == self.category,
                    component_id=f"cat_{category.id}"
                )
                category_group.add(cb)
                panel.add(cb)
        
        # Back button
        panel.add(CheckBox("⬅️ Back", False, component_id="back"))
        
        self.current_panel = panel
        return panel

    def _handle_type_change(self, checkbox: CheckBox):
        """Handle transaction type change and reset category"""
        self.transaction_type = checkbox.component_id
        self.category = None

    async def fetch_data(self, user_id: int):
        """Fetch accounts and categories for the user"""
        self.accounts = await get_user_accounts(user_id)
        self.income_cats, self.expense_cats = await ensure_user_has_categories(user_id)

    async def display_on(self, update: Update, text: str, markup):
        """Display the panel on the given update"""
        try:
            if update.message:
                await update.message.reply_text(
                    text=text,
                    reply_markup=markup.render(),
                    parse_mode="HTML"
                )
            elif update.callback_query:
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=markup.render(),
                    parse_mode="HTML"
                )
        except BadRequest as e:
            print(f"No modifications needed: {e.message}")
