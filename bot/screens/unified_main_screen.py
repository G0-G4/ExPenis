from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, Application

from bot.components.main_menu import MainMenu
from bot.components.transaction_edit import TransactionEdit
from bot.screens.screen import Screen


class UnifiedMainScreen(Screen):
    """Unified main screen that manages different UI states through components"""
    
    def __init__(self, application: Application):
        super().__init__()
        self.application = application
        
        # Register handlers
        application.add_handler(CommandHandler('start', self.start_handler))
        self.press_handler = CallbackQueryHandler(
            self.handle_user_presses,
            pattern='^cb_|^back$|^enter_transaction$|^view_transaction_|^separator$'
        )
        self.input_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_user_messages)
        application.add_handler(self.press_handler)
        application.add_handler(self.input_handler)

    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - show main menu"""
        user_id = update.message.from_user.id
        user_state = self.get_user_state(update, context)
        user_state['current_component'] = 'main_menu'
        
        await self.init(update, context)
        await self.display_on(update, await self.get_message(update, context), self.render(update, context))

    def get_user_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get or create user-specific state"""
        if 'update' not in context.user_data and update.callback_query is not None:
            context.user_data['update'] = update
        context.user_data['user_id'] = context._user_id
        
        if 'unified_main_screen' not in context.user_data:
            context.user_data['unified_main_screen'] = {
                'main_menu': MainMenu(on_change=self.on_main_menu_change),
                'transaction_edit': TransactionEdit(on_change=self.on_transaction_edit_change),
                'current_component': 'main_menu',
                'message': 'Welcome!'
            }
        return context.user_data['unified_main_screen']

    async def on_main_menu_change(self, component, update, context):
        """Handle main menu component changes (like viewing transaction details)"""
        # For now, just refresh the main menu
        user_state = self.get_user_state(update, context)
        await user_state['main_menu'].fetch_data(context.user_data['user_id'], context)

    async def on_transaction_edit_change(self, component, update, context):
        """Handle transaction edit completion - return to main menu"""
        user_state = self.get_user_state(update, context)
        user_state['current_component'] = 'main_menu'
        user_state['transaction_edit'].clear_state()
        
        # Refresh main menu data
        await user_state['main_menu'].fetch_data(context.user_data['user_id'], context)

    async def initiated(self, update, context):
        """Check if current component is initiated"""
        user_state = self.get_user_state(update, context)
        current_component = user_state['current_component']
        
        if current_component == 'main_menu':
            return user_state['main_menu'].initiated
        elif current_component == 'transaction_edit':
            return user_state['transaction_edit'].initiated
        return False

    async def init(self, update, context):
        """Initialize current component"""
        user_state = self.get_user_state(update, context)
        current_component = user_state['current_component']
        user_id = context.user_data['user_id']
        
        if current_component == 'main_menu':
            await user_state['main_menu'].init(user_id, context)
        elif current_component == 'transaction_edit':
            await user_state['transaction_edit'].init(user_id, update)

    async def clear_state(self, update, context):
        """Clear component state"""
        user_state = self.get_user_state(update, context)
        current_component = user_state['current_component']
        
        if current_component == 'transaction_edit':
            user_state['transaction_edit'].clear_state()

    async def handle_message(self, update, context, message):
        """Handle text messages - delegate to current component"""
        user_state = self.get_user_state(update, context)
        current_component = user_state['current_component']
        
        if current_component == 'transaction_edit':
            return await user_state['transaction_edit'].handle_message(update, context, message)
        return False

    async def handle_callback(self, update, context, query_data: str):
        """Handle callback queries - delegate to components or handle navigation"""
        user_state = self.get_user_state(update, context)
        
        # Handle navigation callbacks
        if query_data == 'enter_transaction':
            user_state['current_component'] = 'transaction_edit'
            await user_state['transaction_edit'].init(context.user_data['user_id'], update)
            return True
        elif query_data.startswith('view_transaction_'):
            # Extract transaction ID and switch to edit mode
            transaction_id = int(query_data.split('_')[-1])
            user_state['current_component'] = 'transaction_edit'
            await user_state['transaction_edit'].init(context.user_data['user_id'], update, transaction_id)
            return True
        elif query_data == 'back':
            user_state['current_component'] = 'main_menu'
            await user_state['main_menu'].fetch_data(context.user_data['user_id'], context)
            return True
        
        # Delegate to current component
        current_component = user_state['current_component']
        if current_component == 'main_menu':
            return await user_state['main_menu'].handle_callback(update, context, query_data)
        elif current_component == 'transaction_edit':
            return await user_state['transaction_edit'].handle_callback(update, context, query_data)
        
        return False

    def render(self, update, context):
        """Render current component"""
        user_state = self.get_user_state(update, context)
        current_component = user_state['current_component']
        
        if current_component == 'main_menu':
            return user_state['main_menu'].render(update, context)
        elif current_component == 'transaction_edit':
            keyboard = user_state['transaction_edit'].render(update, context)
            # Add back button for transaction edit
            from telegram import InlineKeyboardButton
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
            return keyboard
        
        return []

    async def get_message(self, update, context):
        """Get message for current component"""
        user_state = self.get_user_state(update, context)
        current_component = user_state['current_component']
        
        if current_component == 'main_menu':
            return user_state['main_menu'].get_message(context)
        elif current_component == 'transaction_edit':
            return user_state['transaction_edit'].get_message()
        
        return "Welcome!"