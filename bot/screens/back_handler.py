from bot.screens.account_selection import ACCOUNT_SELECTION_SCREEN, account_selection_screen
from bot.screens.add_acount import ACCOUNT_NAME, ADD_ACCOUNT_SCREEN, account_name, add_account
from bot.screens.category_selection import CATEGORY_SELECTION_SCREEN, category_selection_screen
from bot.screens.main import MAIN_SCREEN, start
from bot.screens.periods import CUSTOM_PERIOD, PERIOD_SELECTION_SCREEN, PERIOD_VIEW_SCREEN, custom_period, \
    period_selection_screen, \
    period_view_screen
from bot.screens.transaction_type_selection import TRANSACTION_TYPE_SELECTION_SCREEN, transaction_type_selection_screen
from bot.screens.transaction_view import TRANSACTION_VIEW_SCREEN, transaction_view_screen
from bot.bot_config import *
from bot.keyboards import  *
async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Get previous state from user_data
    previous_state = get_previous_state(context)
    context.user_data['set_previous'] = False

    # Handle going back to previous state
    if previous_state == MAIN_SCREEN:
        return await start(update, context)
    if previous_state == ACCOUNT_SELECTION_SCREEN:
        return await account_selection_screen(update, context)
    elif previous_state == TRANSACTION_TYPE_SELECTION_SCREEN:
        return await transaction_type_selection_screen(update, context)
    elif previous_state == CATEGORY_SELECTION_SCREEN:
        return await category_selection_screen(update, context)
    elif previous_state == TRANSACTION_VIEW_SCREEN:
        return await transaction_view_screen(update, context)
    elif previous_state == ADD_ACCOUNT_SCREEN:
        return await add_account(update, context)
    elif previous_state == ACCOUNT_NAME:
        return await account_name(update, context)
    elif previous_state == PERIOD_SELECTION_SCREEN:
        return await period_selection_screen(update, context)
    elif previous_state == PERIOD_VIEW_SCREEN:
        return await period_view_screen(update, context)
    elif previous_state == CUSTOM_PERIOD:
        return await custom_period(update, context)
    return previous_state