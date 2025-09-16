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
                'components': {
                    'main_menu': MainMenu(on_change=self.on_main_menu_change),
                    'transaction_edit': TransactionEdit(on_change=self.on_transaction_edit_change),
                },
                'current_component': 'main_menu',
                'message': 'Welcome!'
            }
        return context.user_data['unified_main_screen']

    async def on_main_menu_change(self, component, update, context):
        """Handle main menu component changes (like viewing transaction details)"""
        # For now, just refresh the main menu
        user_state = self.get_user_state(update, context)
        await user_state['components']['main_menu'].fetch_data(context.user_data['user_id'], context)

    async def on_transaction_edit_change(self, component, update, context):
        """Handle transaction edit completion - return to main menu"""
        user_state = self.get_user_state(update, context)
        user_state['current_component'] = 'main_menu'
        await user_state['components']['transaction_edit'].clear_state(update, context)
        
        # Refresh main menu data
        await user_state['components']['main_menu'].fetch_data(context.user_data['user_id'], context)

    async def initiated(self, update, context):
        """Check if current component is initiated"""
        user_state = self.get_user_state(update, context)
        current_component_name = user_state['current_component']
        current_component = user_state['components'].get(current_component_name)
        
        return current_component.initiated if current_component else False

    async def init(self, update, context, *args, **kwargs):
        """Initialize current component with consistent signatures"""
        user_state = self.get_user_state(update, context)
        current_component_name = user_state['current_component']
        current_component = user_state['components'].get(current_component_name)
        user_id = context.user_data['user_id']
        
        if current_component:
            await current_component.init(update, context, user_id=user_id)
        
        # Mark the UnifiedMainScreen itself as initiated
        self.initiated = True

    async def clear_state(self, update, context):
        """Clear component state with consistent signatures"""
        user_state = self.get_user_state(update, context)
        current_component_name = user_state['current_component']
        current_component = user_state['components'].get(current_component_name)
        
        if current_component:
            await current_component.clear_state(update, context)
        
        # Mark the UnifiedMainScreen as not initiated
        self.initiated = False

    async def handle_message(self, update, context, message):
        """Handle text messages - delegate to current component"""
        user_state = self.get_user_state(update, context)
        current_component_name = user_state['current_component']
        current_component = user_state['components'].get(current_component_name)
        
        if current_component and hasattr(current_component, 'handle_message'):
            return await current_component.handle_message(update, context, message)
        return False

    async def handle_callback(self, update, context, query_data: str):
        """Handle callback queries - delegate to components or handle navigation"""
        user_state = self.get_user_state(update, context)
        
        # Handle navigation callbacks
        if query_data == 'enter_transaction':
            # Clear transaction edit state for new transaction
            await user_state['components']['transaction_edit'].clear_state(update, context)
            user_state['current_component'] = 'transaction_edit'
            await user_state['components']['transaction_edit'].init(update, context, user_id=context.user_data['user_id'])
            return True
        elif query_data.startswith('view_transaction_'):
            # Extract transaction ID and switch to edit mode
            transaction_id = int(query_data.split('_')[-1])
            user_state['current_component'] = 'transaction_edit'
            await user_state['components']['transaction_edit'].init(update, context, user_id=context.user_data['user_id'], transaction_id=transaction_id)
            return True
        elif query_data == 'back':
            user_state['current_component'] = 'main_menu'
            await user_state['components']['main_menu'].fetch_data(context.user_data['user_id'], context)
            return True
        
        # Delegate to current component
        current_component_name = user_state['current_component']
        current_component = user_state['components'].get(current_component_name)
        
        if current_component and hasattr(current_component, 'handle_callback'):
            return await current_component.handle_callback(update, context, query_data)
        
        return False

    def render(self, update, context):
        """Render current component"""
        user_state = self.get_user_state(update, context)
        current_component_name = user_state['current_component']
        current_component = user_state['components'].get(current_component_name)
        
        if not current_component:
            return []
            
        keyboard = current_component.render(update, context)
        
        # Add back button for transaction edit
        if current_component_name == 'transaction_edit':
            from telegram import InlineKeyboardButton
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
            
        return keyboard

    async def get_message(self, update, context):
        """Get message for current component"""
        user_state = self.get_user_state(update, context)
        current_component_name = user_state['current_component']
        current_component = user_state['components'].get(current_component_name)
        
        if not current_component:
            return "Welcome!"
            
        return await current_component.get_message(update, context)