from datetime import date

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from core.helpers import format_percentage, get_target_date
from bot.messages import *
from bot.bot_config import *
from bot.keyboards import  *
from core.service.transaction_service import get_custom_period_statistics

PERIOD_SELECTION_SCREEN = "PERIOD_SELECTION_SCREEN"
async def period_selection_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show period selection menu"""
    push_state(context)
    keyboard = [
        [InlineKeyboardButton("📅 Today", callback_data="view_period_day_0")],
        [InlineKeyboardButton("📅 This Week", callback_data="view_period_week_0")],
        [InlineKeyboardButton("📅 This Month", callback_data="view_period_month_0")],
        [InlineKeyboardButton("📅 This Year", callback_data="view_period_year_0")],
        [InlineKeyboardButton("🔍 Custom Period", callback_data="choose_custom_period")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back")]
    ]
    context.user_data['update'] = update

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=PERIOD_VIEW_MESSAGE,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            text=PERIOD_VIEW_MESSAGE,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    context.user_data['previous_state'] = PERIOD_SELECTION_SCREEN
    return PERIOD_SELECTION_SCREEN


PERIOD_VIEW_SCREEN = "PERIOD_VIEW_SCREEN"
async def period_view_screen(update, context: ContextTypes.DEFAULT_TYPE, recursive_call=False):
    push_state(context)
    query = update.callback_query
    if not recursive_call and query.data.startswith('view_period_'):
        parts = query.data.split('_')
        period_type = parts[2]  # day, week, month, year
        offset = int(parts[3])  # offset for navigation
        context.user_data['date'] = str(date.today())
        context.user_data['period_type'] = period_type
        context.user_data['offset'] = offset
        context.user_data['user_id'] = query.from_user.id
        return await period_view_screen(update, context, True)
    if recursive_call and 'date' in context.user_data:
        context.user_data['date'] = str(date.today())
        return await view_period_stats(update, context, context.user_data['period_type'] , context.user_data['offset'])

    elif query and query.data.startswith('prev_') or query.data.startswith('next_'):
        parts = query.data.split('_')
        direction = parts[0]  # prev or next
        period_type = parts[1]
        current_offset = int(parts[2])

        # Calculate new offset
        offset = current_offset - 1 if direction == 'prev' else current_offset + 1
        await view_period_stats(update, context, period_type, offset)

    elif query and query.data == 'choose_custom_period':

        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="📅 <b>Please enter a date in one of these formats:</b>\n"
                 "<pre>YYYY</pre>          (for a year)\n"
                 "<pre>YYYY-MM</pre>       (for a month)\n"
                 "<pre>YYYY-MM-DD</pre>    (for a specific date)",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    return PERIOD_VIEW_SCREEN

async def view_period_stats(update: Update, context: ContextTypes.DEFAULT_TYPE,
                            period_type: str, offset: int = 0):
    """View statistics for a specific period"""

    query = context.user_data['update'].callback_query
    # Get period data
    period_data = await get_custom_period_statistics(
        context.user_data['user_id'], context.user_data['period_type'], context.user_data['date'], offset
    )

    # Add navigation keyboard - this will be used in both cases
    keyboard = get_period_navigation_keyboard(period_type, offset, context.user_data['user_id'])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if not period_data or (not period_data["income_categories"] and not period_data["expense_categories"]):
        await query.edit_message_text(
            text=f"{PERIOD_STATS_MESSAGE}\n\n{NO_DATA_MESSAGE}",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return

    # Format message
    message_text = f"{PERIOD_STATS_MESSAGE}\n"
    message_text += f"<pre>Period: {period_data['period_label']}</pre>\n\n"

    # Add income categories
    if period_data["income_categories"]:
        message_text += "<b>💰 Income by Category:</b>\n"
        total_income = sum(cat["total"] for cat in period_data["income_categories"])
        for category in period_data["income_categories"]:
            percentage = (category["total"] / total_income * 100) if total_income > 0 else 0
            message_text += f"  {category['category']:<15} {format_amount(category['total']):>12} ({format_percentage(percentage)}%)\n"
        message_text += f"  {'Total Income':<15} <b>{format_amount(total_income):>12}</b>\n\n"

    # Add expense categories
    if period_data["expense_categories"]:
        message_text += "<b>💸 Expenses by Category:</b>\n"
        total_expense = sum(cat["total"] for cat in period_data["expense_categories"])
        for category in period_data["expense_categories"]:
            percentage = (category["total"] / total_expense * 100) if total_expense > 0 else 0
            message_text += f"  {category['category']:<15} {format_amount(category['total']):>12} ({format_percentage(percentage)}%)\n"
        message_text += f"  {'Total Expenses':<15} <b>{format_amount(total_expense):>12}</b>\n\n"

    # Add net total
    net_total = period_data["net_total"]
    net_total_formatted = format_amount(abs(net_total))
    if net_total >= 0:
        message_text += f"<b>📊 Net Total:       +{net_total_formatted}</b>"
    else:
        message_text += f"<b>📊 Net Total:       -{net_total_formatted}</b>"

    await query.edit_message_text(
        text=message_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

CUSTOM_PERIOD = "CUSTOM_PERIOD"
async def custom_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount input from user"""
    if not update.message or not update.message.from_user:
        return CUSTOM_PERIOD

    date_input = update.message.text.strip()

    # Determine period type based on input format
    if len(date_input) == 4 and date_input.isdigit():
        # YYYY format - year
        period_type = 'year'
    elif (len(date_input) == 7 and
          date_input[4] == '-' and
          date_input[:4].isdigit() and
          date_input[5:].isdigit()):
        # YYYY-MM format - month
        period_type = 'month'
    elif (len(date_input) == 10 and
          date_input[4] == '-' and
          date_input[7] == '-' and
          date_input[:4].isdigit() and
          date_input[5:7].isdigit() and
          date_input[8:].isdigit()):
        # YYYY-MM-DD format - day
        period_type = 'day'
    else:
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "❌ <b>Invalid date format.</b> Please use one of these formats:\n"
            "<pre>YYYY</pre>          (for a year)\n"
            "<pre>YYYY-MM</pre>       (for a month)\n"
            "<pre>YYYY-MM-DD</pre>    (for a specific date)",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return CUSTOM_PERIOD

    try:
        context.user_data['date'] = get_target_date(period_type, date_input)
        context.user_data['period_type'] = period_type
        context.user_data['offset'] = 0
        context.user_data['user_id'] = update.message.from_user.id
        return await period_view_screen(update, context, True)

    except ValueError as e:
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "❌ <b>Invalid date format.</b> Please try again.",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return CUSTOM_PERIOD

def get_period_navigation_keyboard(period_type, period_value, user_id):
    """Create navigation keyboard for period viewing"""
    keyboard = []

    # Navigation buttons
    nav_row = [
        InlineKeyboardButton("⬅️ Previous", callback_data=f"prev_{period_type}_{period_value}"),
        InlineKeyboardButton("Next ➡️", callback_data=f"next_{period_type}_{period_value}")
    ]
    keyboard.append(nav_row)

    # Back to period selection
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])

    return keyboard