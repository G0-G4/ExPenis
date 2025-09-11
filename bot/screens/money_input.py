from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from core.helpers import format_percentage
from bot.messages import *
from bot.bot_config import *
from bot.keyboards import  *
from core.service.transaction_service import create_transaction, get_todays_totals, \
    get_todays_transactions, \
    update_transaction
from core.service.account_service import AccountService

MONEY_INPUT_SCREEN = 'MONEY_INPUT_SCREEN'
async def money_input_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    push_state(context)
    query = update.callback_query
    await query.answer()
    transaction_type, category = query.data.split("_")
    context.user_data['transaction_category'] = category

    user_id = query.from_user.id
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=f"🏷️ <b>Selected category: {category}</b>\n\n{AMOUNT_PROMPT_MESSAGE}",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    context.user_data['previous_state'] = MONEY_INPUT_SCREEN
    return MONEY_INPUT_SCREEN

async def money_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        amount_text = update.message.text
        if not amount_text:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_type_selection")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                INVALID_AMOUNT_MESSAGE,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return

        amount = float(amount_text)

        # Get transaction details
        transaction_type = context.user_data['transaction_type']
        category = context.user_data['transaction_category']
        account_id = context.user_data['account_id']

        # Format transaction for display
        formatted_amount = format_amount(amount)
        if transaction_type == 'income':
            transaction_text = f"🟢 Income: +{formatted_amount} ({category})"
        else:
            transaction_text = f"🔴 Expense: -{formatted_amount} ({category})"

        # Save transaction to database using transaction service
        try:
            if context.user_data['edit_transaction']:
                transaction = await update_transaction(
                    transaction_id=context.user_data['transaction'].id,
                    user_id=user_id,
                    amount=amount,
                    category=category,
                    transaction_type=transaction_type,
                    account_id=account_id
                )
            else:
                transaction = await create_transaction(
                    user_id=user_id,
                    amount=amount,
                    category=category,
                    transaction_type=transaction_type,
                    account_id=account_id
                )

            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"{TRANSACTION_RECORDED_MESSAGE}\n<pre>{transaction_text}</pre>\n\n{TRANSACTION_ID_MESSAGE} {transaction.id}\n\n{THANK_YOU_MESSAGE}",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            # logger.error(f"Error saving transaction: {e}")
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"{TRANSACTION_RECORDED_MESSAGE}\n<pre>{transaction_text}</pre>\n\n{ERROR_SAVING_TRANSACTION_MESSAGE}\n\n{THANK_YOU_MESSAGE}",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

        # Clear user data for this transaction
        self.user_data[user_id] = {}

        # Show main menu with today's transaction

        return await self.start(update, context)

    except ValueError:
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_type_selection")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            INVALID_AMOUNT_MESSAGE,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )