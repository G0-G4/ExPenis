from typing import ClassVar, Sequence

from telegram import InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from tuican import get_user_id
from tuican.components import Button, CheckBox, Component, ExclusiveCheckBoxGroup, Input, Screen, ScreenGroup
from tuican.validation import identity

from bot.components.transaction_screen import render_by_n
from core.models.category import Category
from core.service.category_service import (
    CategoryType, create_category,
    delete_category_by_id, get_user_categories,
    update_category,
)


class CategoriesScreen(Screen):
    def __init__(self, group: ScreenGroup):
        self.group = group

        self.type_group = ExclusiveCheckBoxGroup(sticky=True)

        self.new_category = Button(text="➕ New Category", on_change=self.new_income_handler)
        self.income_tab = CheckBox(text="🟢 Income (+)", component_id="income", selected=True, group=self.type_group)
        self.expense_tab = CheckBox(text="🔴 Expense (-)", component_id="expense", group=self.type_group)

        self.income_categories = None
        self.expense_categories = None
        self.income_buttons = []
        self.expense_buttons = []
        super().__init__([self.new_category, self.income_tab, self.expense_tab], message="categories")

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        await self.init_if_necessary(get_user_id(update))

        income_cb = self.type_group.get_selected() is not None and self.type_group.get_selected().component_id == "income"
        buttons = self.income_buttons if income_cb else self.expense_buttons

        layout = [
            [self.income_tab.render(update, context), self.expense_tab.render(update, context)],
            *render_by_n(update, context, buttons),
            [self.new_category.render(update, context)]
        ]
        return layout

    async def new_income_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        self.income_categories = None
        self.income_buttons = []
        self.expense_categories = None
        self.expense_buttons = []
        screen = CategoryCreateScreen(self.group, self.type_group.get_selected().component_id)
        await self.group.go_to_screen(update, context, screen)

    async def back_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await self.group.go_back(update, context)

    async def edit_category_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str,
                                    cmp: Component):
        self.income_categories = None
        self.income_buttons = []
        self.expense_categories = None
        self.expense_buttons = []
        screen = CategoryEditScreen(self.group, cmp.data)
        await self.group.go_to_screen(update, context, screen)

    async def init_if_necessary(self, user_id: int):
        if self.income_categories is None or self.expense_categories is None:
            self.income_categories, self.expense_categories = await get_user_categories(user_id)
            for category in self.income_categories:
                button = Button(text=category.name, component_id=str(category.id), on_change=self.edit_category_handler)
                button.data = category
                self.income_buttons.append(button)
                self.add_component(button)
            for category in self.expense_categories:
                button = Button(text=category.name, component_id=str(category.id), on_change=self.edit_category_handler)
                button.data = category
                self.expense_buttons.append(button)
                self.add_component(button)


class CategoryCreateScreen(Screen):
    def __init__(self, group: ScreenGroup, category_type: CategoryType):
        self.group = group
        self.type = category_type
        self.name = Input[str](identity, text="Name:")
        self.save = Button(text="✅ Save", on_change=self.save_handler)
        self.back = Button(text="⬅️ Back", on_change=self.back_handler)

        super().__init__([self.name, self.save, self.back],
                         message=f"Create new {'income' if category_type == 'income' else 'expense'} category")

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        layout = [[self.name.render(update, context)]]
        if self.name.value is not None:
            layout += [[self.save.render(update, context)]]
        return layout + [[self.back.render(update, context)]]

    async def save_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if self.name.value:
            await create_category(get_user_id(update), self.name.value, self.type)
            await self.group.go_back(update, context)

    async def back_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await self.group.go_back(update, context)


class CategoryEditScreen(CategoryCreateScreen):
    def __init__(self, group: ScreenGroup, category: Category):
        super().__init__(group, category.type)
        self.message = "edit category"
        self.category = category
        self.name.value = category.name
        self.delete = Button(text="🗑 Delete", on_change=self.delete_handler)
        self.add_component(self.delete)

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        layout = await super().get_layout(update, context)
        return layout + [[self.delete.render(update, context)]]

    async def save_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        self.category.name = self.name.value
        await update_category(self.category)
        await self.group.go_back(update, context)

    async def delete_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        screen = DeleteScreen(self.category.id, self.group)
        await self.group.go_to_screen(update, context, screen)


class DeleteScreen(Screen):

    def __init__(self, category_id: int, group: ScreenGroup):
        self.group = group
        self.category_id = category_id
        self.delete = Button(text="🗑 Delete", on_change=self.delete_handler)
        self.cancel = Button(text="❌ Cancel", on_change=self.cancel_handler)
        super().__init__([self.delete, self.cancel], message="Удалить?")

    async def get_layout(self, update, context) -> Sequence[Sequence[InlineKeyboardButton]]:
        return [
            [self.delete.render(update, context), self.cancel.render(update, context)]
        ]

    async def cancel_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await self.group.go_back(update, context)

    async def delete_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await delete_category_by_id(self.category_id)
        await self.group.go_home(update, context)


class CategoriesMain(ScreenGroup):
    description: ClassVar[str] = "categories"

    def __init__(self):
        self.main = CategoriesScreen(self)
        super().__init__(self.main)
