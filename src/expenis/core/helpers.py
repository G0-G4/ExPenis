from datetime import date


def format_amount(amount):
    """Format amount with thousands separator and 2 decimal places"""
    return f"{amount:_.2f}".replace("_", " ")


def format_date(dt: date) -> str:
    """Format date as 'Mon 15 Jan'"""
    return dt.strftime("%a %d %b %y")


def format_long_date(dt: date) -> str:
    """Format date as 'Monday, 15 January'"""
    return dt.strftime("%A, %d %B")


def format_percentage(value):
    """Format percentage with 1 decimal place"""
    return f"{value:.1f}"
