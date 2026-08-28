from playwright.sync_api import Page, expect

from e2e.helpers import (
    PASSWORD,
    expect_login_screen,
    expect_transactions_screen,
    login_via_ui,
    open_app,
    register_via_api,
    unique_username,
)


def test_login_with_valid_account_opens_transactions(page: Page) -> None:
    username = unique_username("e2e-login")
    register_via_api(username, PASSWORD)

    open_app(page)
    login_via_ui(page, username, PASSWORD)
    expect_transactions_screen(page)


def test_login_with_wrong_password_stays_on_login(page: Page) -> None:
    username = unique_username("e2e-bad")
    register_via_api(username, PASSWORD)

    open_app(page)
    login_via_ui(page, username, "wrong-password")
    expect_login_screen(page)
    expect(page.get_by_role("heading", name="Transactions")).to_have_count(0)
