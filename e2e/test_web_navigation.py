import re

from playwright.sync_api import Page, expect

from e2e.helpers import (
    PASSWORD,
    expect_login_screen,
    expect_transactions_screen,
    fill_textbox,
    login_via_ui,
    open_app,
    open_section,
    register_via_api,
    unique_username,
)


def expect_side_menu(page: Page) -> None:
    for name in ("Accounts", "Transactions", "Categories"):
        expect(page.get_by_role(
            "button", name=re.compile(rf"^{name} Tab \d+ of \d+$"),
        )).to_be_visible()
    expect(page.get_by_role("button", name=re.compile(r"^Settings(?: Settings)?$"))).to_be_visible()
    expect(page.get_by_role("button", name=re.compile(r"^Monthly analytics(?: Monthly analytics)?$"))).to_be_visible()


def test_web_side_menu_survives_routes_resize_and_logout(page: Page, tmp_path) -> None:
    page.set_viewport_size({"width": 1280, "height": 900})
    username = unique_username("e2e-navigation")
    register_via_api(username, PASSWORD)
    open_app(page)
    login_via_ui(page, username, PASSWORD)
    expect_transactions_screen(page)

    page.get_by_role("button", name=re.compile(r"^Settings(?: Settings)?$")).click()
    expect(page.get_by_role("heading", name=re.compile(r"^Settings(?: Settings)?$"))).to_be_visible()
    expect_side_menu(page)
    page.get_by_role("button", name="Экспорт операций", exact=True).click()
    expect(page.get_by_role("heading", name="Экспорт операций")).to_be_visible()
    expect_side_menu(page)
    page.screenshot(path=str(tmp_path / "export-with-side-menu.png"))
    page.get_by_role("button", name="Back", exact=True).click()
    expect(page.get_by_role("heading", name=re.compile(r"^Settings(?: Settings)?$"))).to_be_visible()
    page.get_by_role("button", name="Change password", exact=True).click()
    expect(page.get_by_role("heading", name="Change Password", exact=True)).to_be_visible()
    expect_side_menu(page)

    # Selecting a main section discards the inner route stack.
    open_section(page, "Categories")
    expect(page.get_by_role("heading", name="Categories", exact=True)).to_be_visible()
    page.get_by_role("button", name="Add category", exact=True).click()
    expect(page.get_by_role("heading", name="New Category", exact=True)).to_be_visible()
    expect_side_menu(page)
    fill_textbox(page, "Category Name", "Navigation demo")

    # Reparenting the content navigator must retain the open form and its input.
    page.set_viewport_size({"width": 390, "height": 844})
    expect(page.get_by_role("heading", name="New Category", exact=True)).to_be_visible()
    expect(page.get_by_role("textbox", name="Category Name").last).to_have_value("Navigation demo")
    expect(page.get_by_role("button", name=re.compile(r"^Accounts Tab"))).to_have_count(0)
    page.set_viewport_size({"width": 1280, "height": 900})
    expect_side_menu(page)
    expect(page.get_by_role("textbox", name="Category Name").last).to_have_value("Navigation demo")
    page.get_by_role("button", name="Create Category", exact=True).click()
    expect(page.get_by_role("heading", name="Categories", exact=True)).to_be_visible()
    page.mouse.move(900, 600)
    page.mouse.wheel(0, 1200)
    category = page.get_by_role("button", name="Navigation demo Expense", exact=True)
    expect(category).to_be_visible()
    category.click()
    expect(page.get_by_role("heading", name="Edit Category", exact=True)).to_be_visible()
    expect_side_menu(page)

    page.get_by_role("button", name=re.compile(r"^Monthly analytics(?: Monthly analytics)?$")).click()
    expect(page.get_by_role("heading", name="Statistics", exact=True)).to_be_visible()
    expect_side_menu(page)
    open_section(page, "Transactions")
    expect_transactions_screen(page)
    page.get_by_role("button", name="Add transaction", exact=True).click()
    expect(page.get_by_role("heading", name="New Transaction", exact=True)).to_be_visible()
    expect_side_menu(page)
    open_section(page, "Accounts")
    page.get_by_role("button", name="Add account", exact=True).click()
    expect(page.get_by_role("heading", name="New Account", exact=True)).to_be_visible()
    expect_side_menu(page)

    open_section(page, "Transactions")
    page.set_viewport_size({"width": 390, "height": 844})
    open_section(page, "Accounts")
    page.get_by_role("button", name="Open menu", exact=True).click()
    page.get_by_role("button", name=re.compile(r"^Settings(?: Settings)?$")).click()
    expect(page.get_by_role("heading", name="Settings", exact=True)).to_be_visible()
    page.set_viewport_size({"width": 1280, "height": 900})
    expect_side_menu(page)

    # Logout must use the root navigator, removing both content and side menu.
    page.get_by_role("button", name=re.compile(r"^Settings(?: Settings)?$")).click()
    page.get_by_role("button", name="Log out", exact=True).click()
    expect_login_screen(page)
    expect(page.get_by_role("button", name=re.compile(r"^Settings(?: Settings)?$"))).to_have_count(0)
