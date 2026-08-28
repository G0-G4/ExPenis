import logging
import os
import time
from re import Pattern

import httpx
from playwright.sync_api import Locator, Page, expect

logger = logging.getLogger("e2e")

API_BASE_URL = os.environ.get("E2E_API_URL", "http://127.0.0.1:8000")
PASSWORD = "testpass123"


def unique_username(prefix: str = "e2e") -> str:
    return f"{prefix}-{int(time.time() * 1000)}"


def log_snapshot(page: Page, label: str) -> None:
    logger.info("%s url=%s", label, page.url)
    try:
        logger.info("%s aria:\n%s", label, page.locator("body").aria_snapshot())
    except Exception as exc:
        logger.info("%s aria failed: %s", label, exc)


def textbox(page: Page, name: str, *, exact: bool = False) -> Locator:
    return page.get_by_role("textbox", name=name, exact=exact).last


def fill_textbox(page: Page, name: str, value: str, *, exact: bool = False) -> None:
    locator = textbox(page, name, exact=exact)
    expect(locator).to_be_visible()
    logger.info("fill %r (%d chars)", name, len(value))
    locator.click()
    current = locator.input_value()
    if current:
        locator.press("ControlOrMeta+A")
        locator.press("Backspace")
    locator.press_sequentially(value, delay=30)
    if "password" not in name.lower():
        expect(locator).to_have_value(value)


def open_app(page: Page) -> None:
    logger.info("open app")
    page.goto("/")
    enable = page.get_by_role("button", name="Enable accessibility")
    if enable.count():
        logger.info("enable flutter semantics placeholder")
        page.evaluate(
            "() => document.querySelector('flt-semantics-placeholder')?.click()"
        )
    log_snapshot(page, "after open_app")


def expect_login_screen(page: Page) -> None:
    logger.info("wait for Login screen")
    expect(page.get_by_role("heading", name="Login")).to_be_visible(timeout=30_000)


def expect_transactions_screen(page: Page) -> None:
    logger.info("wait for Transactions screen")
    expect(page.get_by_role("heading", name="Transactions")).to_be_visible(
        timeout=30_000,
    )


def login_via_ui(page: Page, username: str, password: str) -> None:
    logger.info("login as %s", username)
    expect_login_screen(page)
    fill_textbox(page, "Username", username)
    fill_textbox(page, "Password", password, exact=True)
    log_snapshot(page, "before Login click")
    page.get_by_role("button", name="Login", exact=True).click()


def register_via_ui(page: Page, username: str, password: str) -> None:
    logger.info("register as %s", username)
    expect_login_screen(page)
    page.get_by_role("button", name="Don't have an account? Register").click()
    expect(page.get_by_role("heading", name="Register")).to_be_visible()
    expect(page.get_by_role("textbox", name="Confirm Password")).to_be_visible()
    expect(page.get_by_role("heading", name="Login")).to_have_count(0)
    fill_textbox(page, "Username", username)
    fill_textbox(page, "Password", password, exact=True)
    fill_textbox(page, "Confirm Password", password)
    log_snapshot(page, "before Register click")
    page.get_by_role("button", name="Register", exact=True).click()


def register_via_api(username: str, password: str) -> None:
    logger.info("POST /api/register username=%s", username)
    response = httpx.post(
        f"{API_BASE_URL}/api/register",
        json={"username": username, "password": password},
        timeout=10.0,
    )
    logger.info("register status=%s", response.status_code)
    response.raise_for_status()


def pick_dropdown(
    page: Page,
    button_name: str | Pattern[str],
    item_name: str | Pattern[str],
) -> None:
    logger.info("pick dropdown %s -> %s", button_name, item_name)
    page.get_by_role("button", name=button_name).click()
    page.get_by_role("menuitem", name=item_name).click()


def confirm_typeahead(page: Page, suggestion: str) -> None:
    """Wait for the TypeAhead overlay, pick the item, then wait until it is gone.

    The overlay is async: checking count() immediately after typing races and
    sees zero items, then AUD/RUB cover Create Account. Do not click headings
    to dismiss — flutter-view intercepts those pointers.
    """
    logger.info("confirm typeahead %s", suggestion)
    suggestion_btn = page.get_by_role("button", name=suggestion, exact=True)
    overlay_marker = page.get_by_role("button", name="AUD", exact=True)
    expect(suggestion_btn.or_(overlay_marker)).to_be_visible(timeout=10_000)
    log_snapshot(page, "typeahead overlay")
    if suggestion_btn.count():
        suggestion_btn.click()
        logger.info("clicked suggestion %s", suggestion)
    else:
        logger.info("suggestion %s not listed, focus Account Name to close overlay", suggestion)
        page.get_by_role("textbox", name="Account Name").click()
    expect(overlay_marker).to_have_count(0)
    expect(suggestion_btn).to_have_count(0)
    logger.info("typeahead overlay closed")
