from datetime import date, datetime

from dateutil.relativedelta import MO, SU, relativedelta


async def calculate_period_dates(period_type: str, offset: int = 0) -> tuple[datetime, datetime, str]:
    """Helper method to calculate date ranges for relative periods"""
    base_date = date.today()

    # Apply offset to get the target base date
    target_base_date = None
    if period_type == "day":
        target_base_date = base_date + relativedelta(days=offset)
    elif period_type == "week":
        # Find the Monday of the current week, then apply week offset
        current_week_start = base_date + relativedelta(weekday=MO(-1))
        target_base_date = current_week_start + relativedelta(weeks=offset)
    elif period_type == "month":
        # Get the first day of the current month, then apply month offset
        current_month_start = base_date.replace(day=1)
        target_base_date = current_month_start + relativedelta(months=offset)
    elif period_type == "year":
        target_base_date = base_date.replace(year=base_date.year + offset)
    else:
        raise ValueError("Invalid period type")

    # Use the common helper to calculate boundaries
    return await _calculate_period_boundaries(target_base_date, period_type)

async def parse_custom_period_dates(period_type: str, date_input: str) -> tuple[datetime, datetime, str]:
    """Helper method to parse custom period dates"""
    target_base_date = None
    try:
        if period_type == "day":
            # Parse YYYY-MM-DD
            target_base_date = datetime.strptime(date_input, "%Y-%m-%d").date()
        elif period_type == "month":
            # Parse YYYY-MM
            target_base_date = datetime.strptime(date_input, "%Y-%m").date().replace(day=1)
        elif period_type == "year":
            # Parse YYYY
            year = int(date_input)
            target_base_date = date(year, 1, 1)
        else:
            raise ValueError("Invalid period type")
    except ValueError as e:
        raise ValueError(f"Invalid date format for {period_type}: {e}")

    # Use the common helper to calculate boundaries
    return await _calculate_period_boundaries(target_base_date, period_type)

async def _calculate_period_boundaries(base_date: date, period_type: str) -> tuple[datetime, datetime, str]:
    """Helper method to calculate start/end dates and label for a given base date and period type."""
    start_date = None
    end_date = None
    period_label = ""

    if period_type == "day":
        target_date = base_date
        start_date = datetime.combine(target_date, datetime.min.time())
        end_date = datetime.combine(target_date, datetime.max.time())
        period_label = target_date.strftime("%Y-%m-%d")
    elif period_type == "week":
        # Find the Monday of the week containing base_date
        week_start = base_date + relativedelta(weekday=MO(-1)) # Monday of the week
        week_end = week_start + relativedelta(weekday=SU)      # Sunday of the week
        start_date = datetime.combine(week_start, datetime.min.time())
        end_date = datetime.combine(week_end, datetime.max.time())
        period_label = f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
    elif period_type == "month":
        # Get the first and last day of the month containing base_date
        month_start = base_date.replace(day=1)
        month_end = month_start + relativedelta(months=1, days=-1)
        start_date = datetime.combine(month_start, datetime.min.time())
        end_date = datetime.combine(month_end, datetime.max.time())
        period_label = month_start.strftime("%B %Y")
    elif period_type == "year":
        year = base_date.year
        start_date = datetime(year, 1, 1, 0, 0, 0)
        end_date = datetime(year, 12, 31, 23, 59, 59)
        period_label = str(year)
    else:
        raise ValueError("Invalid period type")

    return start_date, end_date, period_label
