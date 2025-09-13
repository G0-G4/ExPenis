
from telegram import Update
from telegram.ext import Application

from bot.components.account_selector import AccountSelector
from bot.components.category_selector import CategorySelector
from bot.bot_config import *
from bot.screens.check_box import Screen

class TransactionEdit(Screen):

    def __init__(self, application: Application):
        super().__init__("")
        self.account_selector = AccountSelector()
        self.category_selector = CategorySelector()

        application.add_handler(CallbackQueryHandler(
            self.handle_user_presses,
            pattern='^cb_|^back$|^enter_transaction$'
        ))

    async def handle_user_presses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        initiated = self.account_selector.initiated and self.category_selector.initiated
        if not self.account_selector.initiated:
            await self.account_selector.init(user_id)
        if not self.category_selector.initiated:
            await self.category_selector.init(user_id, update)
        handle_account = await self.account_selector.handle_callback(query.data)
        handle_category = await self.category_selector.handle_callback(query.data)
        if not initiated or handle_account or handle_category:
            await self.display_on(
                update,
                "transaction edit",
                self
            )

    def render(self):
        return self.account_selector.render() + self.category_selector.render()

