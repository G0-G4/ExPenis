from typing import Sequence

from telegram import InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from tuican.components import Component


def render_by_n(update: Update, context: ContextTypes.DEFAULT_TYPE, cmp: list[Component], n: int = 3) -> Sequence[
    Sequence[InlineKeyboardButton]]:
    keyboard = []
    row = []
    for component in cmp:
        row.append(component.render(update, context))
        if len(row) == n:
            keyboard.append(row)
            row = []
    if len(row):
        keyboard.append(row)
    return keyboard
