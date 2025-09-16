from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, Application

from bot.components.main_menu import MainMenu
from bot.components.transaction_edit import TransactionEdit
from bot.screens.screen import Screen
from core.service.transaction_service import get_todays_totals, get_todays_transactions, get_transaction_by_id
from core.service.account_service import get_user_accounts, calculate_account_balance
from core.service.category_service import ensure_user_has_categories


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
            # Initialize with empty components - will be populated with data later
            context.user_data['unified_main_screen'] = {
                'components': {
                    'main_menu': None,
                    'transaction_edit': None,
                },
                'current_component': 'main_menu',
                'message': 'Welcome!'
            }
        return context.user_data['unified_main_screen']

    async def on_main_menu_change(self, component, update, context):
        """Handle main menu component changes (like viewing transaction details)"""
        # Refresh main menu data
        user_state = self.get_user_state(update, context)
        await self._ensure_main_menu_data(update, context)

    async def on_transaction_edit_change(self, component, update, context):
        """Handle transaction edit completion - return to main menu"""
        user_state = self.get_user_state(update, context)
        user_state['current_component'] = 'main_menu'
        
        # Refresh main menu data and recreate component
        await self._ensure_main_menu_data(update, context)

    async def init(self, update, context, *args, **kwargs):
        """Initialize current component with data orchestration"""
        user_state = self.get_user_state(update, context)
        current_component_name = user_state['current_component']
        
        if current_component_name == 'main_menu':
            await self._ensure_main_menu_data(update, context)
        elif current_component_name == 'transaction_edit':
            await self._ensure_transaction_edit_data(update, context)
        
        # Mark the UnifiedMainScreen itself as initiated
        self.initiated = True

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
            # Switch to transaction edit for new transaction
            # Clear any existing transaction_edit component to start fresh
            user_state['components']['transaction_edit'] = None
            user_state['current_component'] = 'transaction_edit'
            await self._ensure_transaction_edit_data(update, context)
            return True
        elif query_data.startswith('view_transaction_'):
            # Extract transaction ID and switch to edit mode
            transaction_id = int(query_data.split('_')[-1])
            # Clear any existing transaction_edit component for fresh edit
            user_state['components']['transaction_edit'] = None
            user_state['current_component'] = 'transaction_edit'
            await self._ensure_transaction_edit_data(update, context, transaction_id=transaction_id)
            return True
        elif query_data == 'back':
            user_state['current_component'] = 'main_menu'
            await self._ensure_main_menu_data(update, context)
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
    
    async def _ensure_main_menu_data(self, update, context):
        """Ensure main menu component has fresh data"""
        user_state = self.get_user_state(update, context)
        user_id = context.user_data['user_id']
        
        # Fetch fresh data
        todays_transactions = await get_todays_transactions(user_id)
        totals = await get_todays_totals(user_id)
        
        # Create or update main menu component
        if user_state['components']['main_menu'] is None:
            user_state['components']['main_menu'] = MainMenu(
                todays_transactions=todays_transactions,
                totals=totals,
                on_change=self.on_main_menu_change
            )
        else:
            user_state['components']['main_menu'].update_data(
                todays_transactions=todays_transactions,
                totals=totals
            )
    
    async def _ensure_transaction_edit_data(self, update, context, transaction_id=None):
        """Ensure transaction edit component has necessary data"""
        user_state = self.get_user_state(update, context)
        user_id = context.user_data['user_id']
        
        # Fetch required data
        accounts = await get_user_accounts(user_id)
        balance_map = {}
        for account in accounts:
            balance_map[account.id] = await calculate_account_balance(account.id, user_id)
        
        income_cats, expense_cats = await ensure_user_has_categories(user_id)
        
        transaction_data = None
        if transaction_id:
            transaction = await get_transaction_by_id(transaction_id)
            if transaction:
                transaction_data = {
                    'id': transaction.id,
                    'account_id': transaction.account_id,
                    'category': transaction.category,
                    'type': transaction.type,
                    'amount': transaction.amount
                }
        
        # Create or update transaction edit component
        if user_state['components']['transaction_edit'] is None:
            user_state['components']['transaction_edit'] = TransactionEdit(
                accounts=accounts,
                balance_map=balance_map,
                income_categories=income_cats,
                expense_categories=expense_cats,
                transaction_data=transaction_data,
                on_change=self.on_transaction_edit_change
            )
        else:
            user_state['components']['transaction_edit'].update_data(
                accounts=accounts,
                balance_map=balance_map,
                income_categories=income_cats,
                expense_categories=expense_cats,
                transaction_data=transaction_data
            )

    async def get_message(self, update, context):
        """Get message for current component"""
        user_state = self.get_user_state(update, context)
        current_component_name = user_state['current_component']
        current_component = user_state['components'].get(current_component_name)
        
        if not current_component:
            return "Welcome!"
            
        return current_component.get_message()