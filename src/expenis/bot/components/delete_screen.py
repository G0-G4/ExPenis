from typing import Any, Callable, Coroutine, Generic, Sequence, TypeVar

from telegram import InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from tuican.components import Button, Screen, ScreenGroup

T = TypeVar('T')
class DeleteScreen[T](Screen):
    def __init__(self, entity_id: T, delete_coroutine: Callable[[T], Coroutine[Any, Any, None]], group: ScreenGroup):

        self.group = group
        self.entity_id = entity_id
        self.delete = Button(text="🗑 Delete", on_change=self.delete_handler)
        self.cancel = Button(text="❌ Cancel", on_change=self.cancel_handler)
        self.delete_coroutine = delete_coroutine
        super().__init__([self.delete, self.cancel], message="Удалить?")

    async def get_layout(self, update, context) -> Sequence[Sequence[InlineKeyboardButton]]:
        return [
            [self.delete.render(update, context), self.cancel.render(update, context)]
        ]

    async def cancel_handler(self,update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await self.group.go_back(update, context)

    async def delete_handler(self,update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await self.delete_coroutine(self.entity_id)
        await self.group.go_home(update, context)