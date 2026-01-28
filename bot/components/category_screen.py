from typing import Sequence

from telegram import InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from tuican import get_user_id
from tuican.components import Button, CheckBox, Component, Input, Screen, ScreenGroup
from tuican.validation import identity

from core.models.category import Category
from core.service.category_service import (
    create_category,
    delete_category,
    get_user_categories,
    update_category,
)


class CategoriesScreen(Screen):
    def __init__(self, group: ScreenGroup):
        self.group = group
        self.new_income = Button(text="➕ New Income", on_change=self.new_income_handler)
        self.new_expense = Button(text="➕ New Expense", on_change=self.new_expense_handler)
        self.back = Button(text="⬅️ Back", on_change=self.back_handler)
        self.income_categories = None
        self.expense_categories = None
        self.category_buttons = []

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        await self.init_if_necessary(get_user_id(update))
        
        layout = [
            [self.new_income.render(update, context)],
            [self.new_expense.render(update, context)],
        ]
        
        if self.income_categories:
            layout.append([InlineKeyboardButton("💰 Income Categories", callback_data="header")])
            for button in self.category_buttons[:len(self.income_categories)]:
                layout.append([button.render(update, context)])
        
        if self.expense_categories:
            layout.append([InlineKeyboardButton("🛒 Expense Categories", callback_data="header")])
            for button in self.category_buttons[len(self.income_categories):]:
                layout.append([button.render(update, context)])
        
        layout.append([self.back.render(update, context)])
        
        return layout

    async def new_income_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        screen = CategoryCreateScreen('income', self.group)
        await self.group.go_to_screen(update, context, screen)

    async def new_expense_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        screen = CategoryCreateScreen('expense', self.group)
        await self.group.go_to_screen(update, context, screen)

    async def back_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await self.group.go_back(update, context)

    async def edit_category_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_id: int):
        screen = CategoryEditScreen(category_id, self.group)
        await self.group.go_to_screen(update, context, screen)

    async def init_if_necessary(self, user_id: int):
        self.income_categories, self.expense_categories = await get_user_categories(user_id)
        if not self.category_buttons:
            for category in self.income_categories + self.expense_categories:
                button = Button(
                    text=f"{'💰' if category.type == 'income' else '🛒'} {category.name}",
                    on_change=lambda u, c, *a, **kw: self.edit_category_handler(u, c, category.id)
                )
                self.category_buttons.append(button)
                self.add_component(button)


class CategoryCreateScreen(Screen):
    def __init__(self, category_type: str, group: ScreenGroup):
        self.group = group
        self.type = category_type
        self.name = Input[str](identity, text="Name:")
        self.save = Button(text="✅ Save", on_change=self.save_handler)
        self.back = Button(text="⬅️ Back", on_change=self.back_handler)
        
        super().__init__([self.name, self.save, self.back], 
                        message=f"Create new {'income' if category_type == 'income' else 'expense'} category")

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        layout = [
            [self.name.render(update, context)],
            [self.save.render(update, context), self.back.render(update, context)]
        ]
        return layout

    async def save_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if self.name.value:
            await create_category(get_user_id(update), self.name.value, self.type)
            await self.group.go_back(update, context)

    async def back_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await self.group.go_back(update, context)


class CategoryEditScreen(Screen):
    def __init__(self, category_id: int, group: ScreenGroup):
        self.group = group
        self.category_id = category_id
        self.category: Category | None = None
        self.name = Input[str](identity, text="Name:")
        self.save = Button(text="✅ Save", on_change=self.save_handler)
        self.delete = Button(text="🗑 Delete", on_change=self.delete_handler)
        self.back = Button(text="⬅️ Back", on_change=self.back_handler)
        
        super().__init__([self.name, self.save, self.delete, self.back], 
                        message="Edit Category")

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        await self.init_if_necessary(get_user_id(update))
        
        layout = [
            [self.name.render(update, context)],
            [self.save.render(update, context), self.delete.render(update, context)],
            [self.back.render(update, context)]
        ]
        return layout

    async def save_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if self.category and self.name.value:
            self.category.name = self.name.value
            await update_category(self.category)
            await self.group.go_back(update, context)

    async def delete_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if self.category:
            await delete_category(self.category)
            await self.group.go_back(update, context)

    async def back_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await self.group.go_back(update, context)

    async def init_if_necessary(self, user_id: int):
        if self.category is None:
            self.category = await get_category_by_id(user_id, self.category_id)
            if self.category:
                self.name.value = self.category.name


class CategoriesMain(ScreenGroup):
    description: ClassVar[str] = "categories"

    def __init__(self):
        super().__init__()
        self.add_screen(CategoriesScreen(self))
