import asyncio

from bot.screens.main import start
from bot.messages import *
from bot.bot_config import *
from bot.keyboards import  *
from core.service.transaction_service import delete_transaction, get_todays_totals, get_todays_transactions, \
    get_transaction_by_id

TRANSACTION_VIEW_SCREEN = 'TRANSACTION_VIEW_SCREEN'
async def transaction_view_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle transaction editing"""
    push_state(context)
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    transaction_id = int(query.data.split('_')[2]) if query.data != 'back' else context.user_data['transaction'].id

    # Get transaction details
    transaction = await get_transaction_by_id(transaction_id)
    context.user_data['transaction'] = transaction #TODO mark selected values when edit

    if not transaction or transaction.user_id != user_id:
        await query.edit_message_text(TRANSACTION_NOT_FOUND_MESSAGE, parse_mode="HTML")
        return

    # Create edit options
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Transaction", callback_data=f"edit_transaction_{transaction.id}")],
        [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{transaction.id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    emoji = "🟢" if transaction.type == "income" else "🔴"
    formatted_amount = format_amount(transaction.amount)
    transaction_text = f"{emoji} {formatted_amount} ({transaction.category})"

    await query.edit_message_text(
        text=f"{EDIT_TRANSACTION_MESSAGE}\n<pre>{transaction_text}</pre>\n\n{CHOOSE_OPTION_MESSAGE}",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    context.user_data['previous_state'] = TRANSACTION_VIEW_SCREEN
    return TRANSACTION_VIEW_SCREEN


async def delete_transaction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a transaction"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    transaction_id = int(query.data.split('_')[1])

    try:
        # Delete the transaction
        result = await delete_transaction(transaction_id, user_id)

        if result:
            await query.edit_message_text(TRANSACTION_DELETED_MESSAGE, parse_mode="HTML")
        else:
            await query.edit_message_text(TRANSACTION_NOT_FOUND_MESSAGE, parse_mode="HTML")
    except Exception as e:
        # logger.error(f"Error deleting transaction: {e}")
        await query.edit_message_text(ERROR_DELETING_TRANSACTION_MESSAGE, parse_mode="HTML")

    # After deletion, show main menu
    await asyncio.sleep(1)
    return await start(update, context)