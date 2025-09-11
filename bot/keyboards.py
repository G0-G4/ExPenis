from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from bot_config import CATEGORIES_PER_ROW
from core.helpers import format_amount
from core.service.account_service import AccountService


def create_category_keyboard(categories, prefix):
    """Create a keyboard with categories arranged in columns"""
    keyboard = []
    row = []
    for i, category in enumerate(categories):
        row.append(InlineKeyboardButton(category, callback_data=f'{prefix}_{category}'))
        if len(row) == CATEGORIES_PER_ROW or i == len(categories) - 1:
            keyboard.append(row)
            row = []
    # Add back button to category selection
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_type_selection")])
    return keyboard

def create_account_keyboard(accounts):
    """Create a keyboard with accounts arranged in columns"""
    keyboard = []
    row = []
    for i, account in enumerate(accounts):
        # Display the account name and its calculated balance
        # We'll calculate the balance here instead of using the stored amount
        row.append(InlineKeyboardButton(f"{account.name}",
                                        callback_data=f'account_{account.id}'))
        if len(row) == CATEGORIES_PER_ROW or i == len(accounts) - 1:
            keyboard.append(row)
            row = []
    # Add back button to account selection
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")])
    return keyboard

async def create_account_keyboard_with_balances(accounts, user_id, account_service: AccountService):
    """Create a keyboard with accounts and their calculated balances"""
    keyboard = []
    row = []
    for i, account in enumerate(accounts):
        # Calculate the current balance for this account
        current_balance = await account_service.calculate_account_balance(account.id, user_id)
        row.append(InlineKeyboardButton(f"{account.name} ({format_amount(current_balance)})",
                                        callback_data=f'account_{account.id}'))
        if len(row) == CATEGORIES_PER_ROW or i == len(accounts) - 1:
            keyboard.append(row)
            row = []
    # Add back button to account selection
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")])
    return keyboard

def get_main_menu_keyboard():
    """Create the main menu keyboard"""
    return [
        [InlineKeyboardButton("➕ Enter Transaction", callback_data='enter_transaction')],
        [InlineKeyboardButton("📊 View by Period", callback_data='select_period')]
    ]

def get_transaction_type_keyboard():
    """Create the transaction type selection keyboard"""
    return [
        [
            InlineKeyboardButton("🟢 Income (+)", callback_data='type_income'),
            InlineKeyboardButton("🔴 Expense (-)", callback_data='type_expense'),
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_account_selection")]
    ]

def get_period_navigation_keyboard(period_type, period_value, user_id):
    """Create navigation keyboard for period viewing"""
    keyboard = []

    # Navigation buttons
    nav_row = [
        InlineKeyboardButton("⬅️ Previous", callback_data=f"prev_{period_type}_{period_value}"),
        InlineKeyboardButton("📅 Choose Date", callback_data=f"choose_custom_period"),
        InlineKeyboardButton("Next ➡️", callback_data=f"next_{period_type}_{period_value}")
    ]
    keyboard.append(nav_row)

    # Back to period selection
    keyboard.append([InlineKeyboardButton("🔙 Back to Periods", callback_data="select_period")])

    return keyboard