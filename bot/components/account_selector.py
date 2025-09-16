from bot.components.check_box import CheckBox, CheckBoxGroup
from bot.components.component import MessageHandlerComponent, UiComponent
from bot.components.panel import Panel
from core.service.account_service import get_user_accounts, calculate_account_balance
from core.helpers import format_amount
class AccountSelector(UiComponent):

    def __init__(self, component_id: str = None, on_change: callable = None):
        super().__init__(component_id, on_change)
        self.accounts = None
        self.account_id = None
        self.accounts = []
        self.balance_map = {}
        self.panel  = Panel()
        self.initiated = False
        self.selected_account = None

    async def init(self, update, context, user_id: int = None):
        """Initialize with consistent signature"""
        if user_id is None:
            user_id = context.user_data.get('user_id') or context._user_id
            
        # Clear panel to avoid duplicates
        self.panel = Panel()
        
        self.accounts = await get_user_accounts(user_id)
        for account in self.accounts:
            balance = await calculate_account_balance(account.id, user_id)
            self.balance_map[account.id] = balance

        # Account selection
        account_group = CheckBoxGroup("accounts",
                                      on_change=self.account_selection_call_back)
        for account in self.accounts:
            cb = CheckBox(
                f"{account.name} ({format_amount(self.balance_map[account.id])})",
                selected=self.account_id == account.id,
                component_id="acc_" + str(account.id),
                group=account_group
            )
            self.panel.add(cb)
        self.initiated = True

    async def clear_state(self, update, context):
        """Reset component state with consistent signature"""
        self.account_id = None
        self.accounts = []
        self.balance_map = {}
        self.panel  = Panel()
        self.initiated = False
        self.selected_account = None

    async def get_message(self, update, context):
        """Get current message to display with consistent signature"""
        if self.selected_account:
            return f"Selected account: {self.selected_account.name}"
        return "Select an account:"
    async def account_selection_call_back(self, cbg: CheckBoxGroup, update, context):
        if cbg.selected_check_box is not None:
            if cbg.selected_check_box.selected:
                self.account_id = int(cbg.selected_check_box.component_id.split("_")[1])
                # todo refactor to avoid loop
                for account in self.accounts:
                    if account.id == self.account_id:
                        self.selected_account = account
            else:
                self.account_id = None
        await self.call_on_change(update, context)

    async def handle_callback(self, update, context, callback_data: str) -> bool:
        return await self.panel.handle_callback(update, context, callback_data)

    def render(self, update, context):
        """Render the account selector UI"""
        return self.panel.render(update, context)