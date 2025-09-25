from bot.components.check_box import CheckBox, ExclusiveCheckBoxGroup
from bot.components.component import MessageHandlerComponent, UiComponent
from bot.components.panel import Panel
from core.helpers import format_amount
class AccountSelector(UiComponent):

    def __init__(self, accounts=None, balance_map=None, selected_account_id=None, component_id: str = None, on_change: callable = None):
        super().__init__(component_id, on_change)
        self.accounts = accounts or []
        self.balance_map = balance_map or {}
        self.account_id = selected_account_id
        self.selected_account = None
        self.panel = Panel()
        self._build_ui()
        self.initiated = len(self.accounts) > 0

    def _build_ui(self):
        """Build UI components from current data"""
        self.panel = Panel()
        
        if not self.accounts:
            return
        
        # Find selected account object
        if self.account_id:
            for account in self.accounts:
                if account.id == self.account_id:
                    self.selected_account = account
                    break

        # Account selection
        account_group = ExclusiveCheckBoxGroup("accounts",
                                               on_change=self.account_selection_call_back)
        for account in self.accounts:
            balance = self.balance_map.get(account.id, 0)
            cb = CheckBox(
                f"{account.name} ({format_amount(balance)})",
                selected=self.account_id == account.id,
                component_id="acc_" + str(account.id),
                group=account_group
            )
            self.panel.add(cb)

    def update_data(self, accounts=None, balance_map=None, selected_account_id=None):
        """Update component data and rebuild UI"""
        if accounts is not None:
            self.accounts = accounts
        if balance_map is not None:
            self.balance_map = balance_map
        if selected_account_id is not None:
            self.account_id = selected_account_id
        
        self._build_ui()
        self.initiated = len(self.accounts) > 0

    def get_message(self):
        """Get current message to display"""
        if self.selected_account:
            return f"Selected account: {self.selected_account.name}"
        return "Select an account:"
    async def account_selection_call_back(self, cbg: ExclusiveCheckBoxGroup, update, context):
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