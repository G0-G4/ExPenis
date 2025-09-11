from bot.messages import *
from bot.bot_config import *
from bot.keyboards import  *
from core.service.category_service import ensure_user_has_categories
CATEGORY_SELECTION_SCREEN = "CATEGORY_SELECTION_SCREEN"
async def category_selection_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    push_state(context)
    query = update.callback_query
    await query.answer()
    type = query.data.split("_")[1] if query.data != 'back' else context.user_data['transaction_type']
    context.user_data['transaction_type'] = type
    user_id = query.from_user.id

    income_cats, expense_cats = await ensure_user_has_categories(user_id)
    if type == 'income':
        cats = income_cats
    else:
        cats = expense_cats
    categories = [cat.name for cat in cats]

    keyboard = create_category_keyboard(categories, type)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=INCOME_CATEGORY_MESSAGE,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

    context.user_data['previous_state'] = CATEGORY_SELECTION_SCREEN
    return CATEGORY_SELECTION_SCREEN