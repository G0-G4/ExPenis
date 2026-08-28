import re
import time

from playwright.sync_api import Page, expect

from e2e.helpers import (
    PASSWORD,
    confirm_typeahead,
    expect_transactions_screen,
    fill_textbox,
    log_snapshot,
    open_app,
    pick_dropdown,
    register_via_ui,
    unique_username,
)


def test_register_create_account_create_expense_transaction(page: Page) -> None:
    username = unique_username("e2e-tx")
    description = f"e2e-tx-{int(time.time() * 1000)}"

    open_app(page)
    register_via_ui(page, username, PASSWORD)
    expect_transactions_screen(page)

    page.get_by_role("tab", name="Accounts").click()
    expect(page.get_by_role("heading", name="Accounts")).to_be_visible()
    page.get_by_role("button", name="Add account").click()
    expect(page.get_by_role("heading", name="New Account")).to_be_visible()
    fill_textbox(page, "Account Name", "Cash")
    fill_textbox(page, "Initial Balance", "1000")
    fill_textbox(page, "Currency Code", "RUB")
    confirm_typeahead(page, "RUB")
    log_snapshot(page, "before Create Account")
    page.get_by_role("button", name="Create Account").click()
    expect(page.get_by_role("heading", name="Accounts")).to_be_visible()
    expect(page.get_by_role("group", name=re.compile(r"^Cash"))).to_be_visible()

    page.get_by_role("tab", name="Transactions").click()
    expect_transactions_screen(page)
    page.get_by_role("button", name="Add transaction").click()
    expect(page.get_by_role("heading", name="New Transaction")).to_be_visible()

    fill_textbox(page, "Amount", "42.5")
    fill_textbox(page, "Description (optional)", description)
    log_snapshot(page, "before Add Transaction")
    pick_dropdown(page, re.compile(r"^Account"), "Cash")
    pick_dropdown(page, re.compile(r"^Category"), re.compile(r"Cafe"))
    page.get_by_role("button", name="Add Transaction").click()

    expect_transactions_screen(page)
    expect(page.get_by_role("button", name=re.compile(description))).to_be_visible()
    expect(page.get_by_text(re.compile(r"Expenses\s+42\.50"))).to_be_visible()
