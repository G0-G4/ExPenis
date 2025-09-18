from datetime import date, datetime
from typing import Literal, Optional
from telegram import InlineKeyboardButton
from telegram.ext import ContextTypes

from bot.components.component import UiComponent
from core.helpers import format_date
from core.helpers import calculate_period_dates

PeriodType = Literal['day', 'week', 'month']

class NavigationArrows(UiComponent):
    def __init__(self,
                 base_date: date,
                 period_type: PeriodType = 'day',
                 offset: int = 0,
                 min_offset: int = -365,  # 1 year back
                 max_offset: int = 0,     # No future dates
                 component_id: str = None,
                 on_change: callable = None):
        super().__init__(component_id, on_change)
        self.period_type = period_type
        self.offset = offset
        self.min_offset = min_offset
        self.max_offset = max_offset
        self.base_date = base_date
        self.initiated = True

    def update_data(self, 
                   period_type: Optional[PeriodType] = None,
                   offset: Optional[int] = None,
                   min_offset: Optional[int] = None,
                   max_offset: Optional[int] = None):
        """Update navigation parameters"""
        if period_type is not None:
            self.period_type = period_type
        if offset is not None:
            self.offset = offset
        if min_offset is not None:
            self.min_offset = min_offset
        if max_offset is not None:
            self.max_offset = max_offset
        self.initiated = True

    def render(self, update, context):
        """Render navigation controls with date display"""
        start_date, end_date = self.get_current_period()
        
        # Format date based on period type
        if self.period_type == 'day':
            date_text = format_date(start_date)
        elif self.period_type == 'week':
            date_text = f"Week of {format_date(start_date)}"
        else:  # month
            date_text = start_date.strftime("%B %Y")
            
        buttons = []
        # Only show left arrow if not at min offset
        # if self.offset > self.min_offset:
        buttons.append(InlineKeyboardButton("◀️", callback_data="nav_prev"))
            
        buttons.append(InlineKeyboardButton(date_text, callback_data="nav_period"))
        
        # Only show right arrow if not at max offset
        # if self.offset < self.max_offset:
        buttons.append(InlineKeyboardButton("▶️", callback_data="nav_next"))
            
        return [buttons]

    def get_current_period(self) -> tuple[date, date]:
        """Get start and end dates for current period"""
        start_date, end_date, _ = calculate_period_dates(self.base_date, self.period_type, self.offset)
        return start_date.date(), end_date.date()

    async def handle_callback(self, update, context, callback_data: str) -> bool:
        """Handle navigation callbacks"""
        if callback_data == "nav_prev":
            self.offset -= 1
            await self.call_on_change(update, context)
            return True
        elif callback_data == "nav_next":
            self.offset += 1
            await self.call_on_change(update, context)
            return True
        elif callback_data == "nav_period":
            prev = self.offset
            self.offset = 0
            if prev != self.offset:
                await self.call_on_change(update, context)
            # TODO implement period selection
            # Cycle through period types
            # period_types: list[PeriodType] = ['day', 'week', 'month']
            # current_idx = period_types.index(self.period_type)
            # new_type = period_types[(current_idx + 1) % len(period_types)]
            # self.update_data(period_type=new_type, offset=0)
            # await self.call_on_change(update, context)
            return True
        return False

    def get_message(self):
        """No message needed as date is shown in buttons"""
        return ""
