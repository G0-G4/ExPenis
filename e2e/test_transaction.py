import re
import time
from pathlib import Path

from playwright.sync_api import Page, expect

from e2e.helpers import (
    PASSWORD,
    confirm_typeahead,
    expect_transactions_screen,
    fill_textbox,
    log_snapshot,
    login_via_ui,
    open_app,
    open_section,
    pick_dropdown,
    register_via_api,
    register_via_ui,
    textbox,
    unique_username,
)


def test_register_create_account_create_expense_transaction(page: Page) -> None:
    username = unique_username("e2e-tx")
    description = f"e2e-tx-{int(time.time() * 1000)}"

    open_app(page)
    register_via_ui(page, username, PASSWORD)
    expect_transactions_screen(page)

    open_section(page, "Accounts")
    expect(page.get_by_role("heading", name="Accounts")).to_be_visible()
    page.get_by_role("button", name="Add account").click()
    expect(page.get_by_role("heading", name="New Account")).to_be_visible()
    fill_textbox(page, "Account Name", "Cash")
    fill_textbox(page, "Initial Balance", "1000/3")
    fill_textbox(page, "Currency Code", "RUB")
    confirm_typeahead(page, "RUB")
    log_snapshot(page, "before Create Account")
    page.get_by_role("button", name="Create Account").click()
    expect(page.get_by_role("heading", name="Accounts")).to_be_visible()
    expect(page.get_by_role("group", name=re.compile(r"^Cash"))).to_be_visible()

    open_section(page, "Transactions")
    expect_transactions_screen(page)
    page.get_by_role("button", name="Add transaction").click()
    expect(page.get_by_role("heading", name="New Transaction")).to_be_visible()

    fill_textbox(page, "Amount", "40+5/2")
    fill_textbox(page, "Description (optional)", description)
    log_snapshot(page, "before Add Transaction")
    pick_dropdown(page, re.compile(r"^Account"), "Cash")
    pick_dropdown(page, re.compile(r"^Category"), re.compile(r"Cafe"))
    page.get_by_role("button", name="Add Transaction").click()

    expect_transactions_screen(page)
    expect(page.get_by_role("button", name=re.compile(description))).to_be_visible()
    expect(page.get_by_text(re.compile(r"Expenses\s+42\.50"))).to_be_visible()

    page.get_by_role("button", name=re.compile(description)).click()
    expect(page.get_by_role("heading", name="Edit Transaction")).to_be_visible()
    page.get_by_role("textbox", name=re.compile(r"^Amount")).last.click()
    expect(
        page.get_by_role("textbox", name=re.compile(r"^Amount")).last
    ).to_have_value("42.5")
    page.get_by_role("button", name="Back", exact=True).click()
    expect_transactions_screen(page)
    open_section(page, "Accounts")
    # The real backend deducts the expense from the evaluated initial balance.
    expect(
        page.get_by_role("group", name=re.compile(r"^Cash.*290\.83", re.S))
    ).to_be_visible()


def test_phone_amount_calculator(page: Page, tmp_path: Path) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    username = unique_username("e2e-calc")
    register_via_api(username, PASSWORD)
    open_app(page)
    login_via_ui(page, username, PASSWORD)
    expect_transactions_screen(page)
    open_section(page, "Accounts")
    page.get_by_role("button", name="Add account").click()
    amount = textbox(page, "Initial Balance")
    amount.click()
    for key, expected in [
        ("1", "1"), ("0", "10"), ("0", "100"),
        ("Divide", "100÷"), ("3", "100÷3"),
    ]:
        page.get_by_role("button", name=key, exact=True).click()
        expect(amount).to_have_value(expected)
    expect(amount).to_have_value("100÷3")
    preview = page.get_by_text("= 33.33", exact=True)
    expect(preview).to_be_visible()
    page.screenshot(path=str(tmp_path / "calculator-portrait.png"))

    # Calculator keys replace the same selection as physical keyboard input.
    amount.click()
    expect(amount).to_be_focused()
    # Flutter processes the canvas caret gesture on its next frame. Wait for
    # that gesture before issuing a native browser selection shortcut.
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    page.keyboard.press("ControlOrMeta+a")
    expect(amount).to_have_js_property("selectionStart", 0)
    expect(amount).to_have_js_property("selectionEnd", len("100÷3"))
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    page.get_by_role("button", name="2", exact=True).click()
    expect(amount).to_have_value("2")
    page.get_by_role("button", name="Divide", exact=True).click()
    page.get_by_role("button", name="0", exact=True).click()
    expect(page.get_by_text("Cannot divide by zero", exact=True)).to_be_visible()
    page.get_by_role("button", name="Delete", exact=True).click()
    page.get_by_role("button", name="4", exact=True).click()
    expect(page.get_by_text("= 0.50", exact=True)).to_be_visible()
    expect(page.get_by_text("Cannot divide by zero", exact=True)).to_have_count(0)

    page.set_viewport_size({"width": 844, "height": 390})
    done = page.get_by_role("button", name="Done", exact=True)
    expect(done).to_be_visible()
    preview = page.get_by_text("= 0.50", exact=True)
    expect(preview).to_be_visible()
    preview_box = preview.bounding_box()
    done_box = done.bounding_box()
    assert preview_box is not None and done_box is not None
    assert preview_box["y"] + preview_box["height"] <= done_box["y"]
    page.screenshot(path=str(tmp_path / "calculator-landscape.png"))
    done.click()
    expect(done).to_have_count(0)
    expect(amount).to_have_value("2÷4")
    expect(page.get_by_role("heading", name="New Account")).to_be_visible()

    page.set_viewport_size({"width": 390, "height": 844})
    amount.click()
    expect(page.get_by_role("button", name="Done", exact=True)).to_be_visible()
    page.get_by_role("textbox", name="Account Name", exact=True).click()
    expect(page.get_by_role("button", name="Done", exact=True)).to_have_count(0)
