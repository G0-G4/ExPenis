
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import Application
from telegram.error import BadRequest
from decimal import Decimal

from bot.components.account_selector import AccountSelector
from bot.components.category_selector import CategorySelector
from bot.components.input import Input
from bot.bot_config import *
from bot.messages import *
from bot.screens.screen import Screen
from core.service.transaction_service import create_transaction

class TransactionEdit(Screen):

    def __init__(self, application: Application):
        super().__init__()
        self.application = application
        self.press_handler = CallbackQueryHandler(
            self.handle_user_presses,
            pattern='^cb_|^back$|^enter_transaction$'
        )
        self.input_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_amount_input)
        application.add_handler(self.press_handler)
        application.add_handler(self.input_handler)

    def get_user_state(self, context: ContextTypes.DEFAULT_TYPE):
        """Get or create user-specific transaction edit state"""
        if 'transaction_edit' not in context.user_data:
            context.user_data['transaction_edit'] = {
                'account_selector': AccountSelector(on_change=self.on_selection_change),
                'category_selector': CategorySelector(on_change=self.on_selection_change),
                'amount_input': Input(on_input=self.on_amount_input),
                'message': "Please select both account and category first",
                'ready_for_input': False,
                'last_update': None
            }
        return context.user_data['transaction_edit']

    async def on_selection_change(self, component):
        # This callback will be called with the component instance
        # We need to find which user's state this belongs to
        # For now, we'll handle this in the main callback handler
        pass
    
    async def handle_amount_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle amount input messages"""
        user_state = self.get_user_state(context)
        amount_input = user_state['amount_input']
        
        if amount_input.is_active():
            await amount_input.handle_message(update, context)

    async def handle_user_presses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        user_state = self.get_user_state(context)
        
        # Store the update for later use
        user_state['last_update'] = update
        
        account_selector = user_state['account_selector']
        category_selector = user_state['category_selector']
        
        initiated = account_selector.initiated and category_selector.initiated
        if not account_selector.initiated:
            await account_selector.init(user_id)
        if not category_selector.initiated:
            await category_selector.init(user_id, update)
            
        handle_account = await account_selector.handle_callback(query.data)
        handle_category = await category_selector.handle_callback(query.data)
        
        # Update ready_for_input state
        user_state['ready_for_input'] = (
            account_selector.account_id is not None and 
            category_selector.category is not None
        )
        
        if user_state['ready_for_input']:
            user_state['message'] = TRANSACTION_INPUT_PROMPT
            user_state['amount_input'].activate()
        else:
            user_state['message'] = "Please select both account and category first"
        
        if not initiated or handle_account or handle_category:
            await self.display_on(update, user_state['message'], user_state)

    def render(self, user_state):
        account_selector = user_state['account_selector']
        category_selector = user_state['category_selector']
        return account_selector.render() + category_selector.render()

    async def on_amount_input(self, input: Input, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.message.from_user.id
            user_state = self.get_user_state(context)
            
            amount_decimal = Decimal(input.value)
            if amount_decimal <= 0:
                raise ValueError("Amount must be positive")

            account_selector = user_state['account_selector']
            category_selector = user_state['category_selector']
            
            transaction = await create_transaction(
                user_id=user_id,
                amount=float(amount_decimal),
                category=category_selector.category,
                transaction_type=category_selector.transaction_type,
                account_id=account_selector.account_id
            )

            chat_id = update.effective_chat.id
            message_id_to_delete = update.message.id
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)

            # Reset the user state for a new transaction
            last_update = user_state['last_update']
            context.user_data['transaction_edit'] = {
                'account_selector': AccountSelector(on_change=self.on_selection_change),
                'category_selector': CategorySelector(on_change=self.on_selection_change),
                'amount_input': Input(on_input=self.on_amount_input),
                'message': "Please select both account and category first",
                'ready_for_input': False,
                'last_update': last_update
            }
            
            new_user_state = context.user_data['transaction_edit']
            await new_user_state['account_selector'].init(user_id)
            await new_user_state['category_selector'].init(user_id, last_update)
            await self.display_on(last_update, new_user_state['message'], new_user_state)

        except Exception as e:
            print("error " + str(e))
    
    async def display_on(self, update: Update, text: str, user_state):
        """Display the transaction edit screen with user-specific state"""
        try:
            if update.message:
                await update.message.reply_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(self.render(user_state)),
                    parse_mode="HTML"
                )
            elif update.callback_query:
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(self.render(user_state)),
                    parse_mode="HTML"
                )
        except BadRequest as e:
            print(f"No modifications needed: {e.message}")
