from bot.screens.main import MAIN_SCREEN
from bot.messages import *
from bot.bot_config import *
from bot.keyboards import  *
from core.service.account_service import AccountService, get_user_accounts

ACCOUNT_SELECTION_SCREEN = 'ACCOUNT_SELECTION_SCREEN'
async def account_selection_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    push_state(context)
    query = update.callback_query
    await query.answer()
    if query.data.startswith('edit'):
        context.user_data['edit_transaction'] = True
    else:
        context.user_data['edit_transaction'] = False
    user_id = query.from_user.id
    accounts = await get_user_accounts(user_id)

    if not accounts:
        # Handle case where user has no accounts
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=NO_ACCOUNTS_MESSAGE,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return MAIN_SCREEN

    # Create account keyboard with calculated balances
    keyboard = await create_account_keyboard_with_balances(accounts, user_id)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=ACCOUNT_SELECTION_MESSAGE,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    context.user_data['previous_state'] = ACCOUNT_SELECTION_SCREEN
    return ACCOUNT_SELECTION_SCREEN