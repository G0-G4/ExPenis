from telegram import Update
from bot.components.check_box import CheckBox, CheckBoxGroup
from bot.components.component import MessageHandlerComponent, UiComponent
from bot.components.panel import Panel
class CategorySelector(UiComponent):

    def __init__(self, income_categories=None, expense_categories=None, selected_category=None, transaction_type='expense', component_id: str = None, on_change: callable = None):
        super().__init__(component_id, on_change)
        self.income_cats = income_categories or []
        self.expense_cats = expense_categories or []
        self.transaction_type = transaction_type
        self.category = selected_category
        self.panel = Panel()
        self.category_map = {}
        self._build_ui()
        self.initiated = len(self.income_cats) > 0 or len(self.expense_cats) > 0

    def _build_ui(self):
        """Build UI components from current data"""
        self.panel = Panel()
        self.category_map = {}
        
        if not (self.income_cats or self.expense_cats):
            return
        
        # Build category map for lookup
        for category in self.expense_cats + self.income_cats:
            self.category_map[category.id] = category
            
        # Transaction type selection
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

        # Category selection
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

        self.panel.add(type_panel)
        self.panel.add(category_panel)

    def update_data(self, income_categories=None, expense_categories=None, selected_category=None, transaction_type=None):
        """Update component data and rebuild UI"""
        if income_categories is not None:
            self.income_cats = income_categories
        if expense_categories is not None:
            self.expense_cats = expense_categories
        if selected_category is not None:
            self.category = selected_category
        if transaction_type is not None:
            self.transaction_type = transaction_type
        
        self._build_ui()
        self.initiated = len(self.income_cats) > 0 or len(self.expense_cats) > 0

    def get_message(self):
        """Get current message to display"""
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
                self._build_ui()
            else:
                self.transaction_type = None
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
