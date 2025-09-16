from telegram import Update
from bot.components.check_box import CheckBox, CheckBoxGroup
from bot.components.component import MessageHandlerComponent, UiComponent
from bot.components.panel import Panel
from core.service.category_service import ensure_user_has_categories
class CategorySelector(UiComponent):

    def __init__(self, component_id: str = None, on_change: callable = None):
        super().__init__(component_id, on_change)
        self.income_cats = []
        self.expense_cats = []
        self.transaction_type = "expense"
        self.category = None
        self.panel = None
        self.category_map = {}
        self.initiated = False

    async def init(self, update, context, user_id: int = None, transaction_type='expense'):
        """Initialize with consistent signature"""
        if user_id is None:
            user_id = context.user_data.get('user_id') or context._user_id
            
        # Clear panel to avoid duplicates
        self.panel = Panel()
        self.category_map = {}
        
        self.transaction_type = transaction_type
        self.income_cats, self.expense_cats = await ensure_user_has_categories(user_id)
        type_group = CheckBoxGroup("type_group",
                                   on_change=self._handle_type_change)
        income_cb = CheckBox(
            "🟢 Income (+)",
            self.transaction_type == 'income',
            component_id="income",
            group=type_group
        )
        expense_cb = CheckBox(
            "🔴 Expense (-)",
            self.transaction_type == 'expense',
            component_id="expense",
            group=type_group
        )
        type_panel = Panel()
        type_panel.add(income_cb)
        type_panel.add(expense_cb)

        category_panel = Panel()
        category_group = CheckBoxGroup("categories",
                                       on_change=self._handle_category_change)
        cats = self.expense_cats if self.transaction_type == 'expense' else self.income_cats
        for category in cats:
            cb = CheckBox(
                category.name,
                category.name == self.category,
                component_id=f"cat_{category.id}",
                group=category_group
            )
            category_group.add(cb)
            category_panel.add(cb)
        for category in self.expense_cats + self.income_cats:
            self.category_map[category.id] = category

        self.panel.add(type_panel)
        self.panel.add(category_panel)
        self.initiated = True

    async def clear_state(self, update, context):
        """Reset component state with consistent signature"""
        self.income_cats = []
        self.expense_cats = []
        self.transaction_type = "expense"
        self.category = None
        self.panel = None
        self.category_map = {}
        self.initiated = False

    async def get_message(self, update, context):
        """Get current message to display with consistent signature"""
        if self.category:
            type_text = "income" if self.transaction_type == 'income' else "expense"
            return f"Selected {type_text} category: {self.category}"
        return f"Select transaction type and category:"

    async def handle_callback(self, update, context, callback_data: str) -> bool:
        return await self.panel.handle_callback(update, context, callback_data)

    async def _handle_type_change(self, cbg: CheckBoxGroup, update: Update, context):
        if cbg.selected_check_box is not None:
            if cbg.selected_check_box.selected:
                self.transaction_type = cbg.selected_check_box.component_id
                self.category = None
                user_id  = update.callback_query.from_user.id
                await self.init(update, context, user_id=user_id, transaction_type=self.transaction_type)
            else:
                self.transaction_type= None
        await self.call_on_change(update, context)

    async def _handle_category_change(self, cbg: CheckBoxGroup, update, context):
        if cbg.selected_check_box is not None:
            if cbg.selected_check_box.selected:
                category_id = int(cbg.selected_check_box.component_id.split("_")[1])
                self.category = self.category_map[category_id].name
            else:
                self.category = None
        await self.call_on_change(update, context)

    def render(self, update, context):
        """Render the category selector UI"""
        return self.panel.render(update, context)

    async def handle_message(self, update, context, message):
        """Handle text input messages"""
        return False
