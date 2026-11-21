"""Run only against a dedicated backend using the same temporary SQLite database."""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Browser, expect

from e2e.helpers import API_BASE_URL, expect_transactions_screen, open_app, open_section

pytestmark = pytest.mark.skipif(
    not os.getenv("E2E_GREETING_DB_PATH"),
    reason="Requires isolated backend and E2E_GREETING_DB_PATH for operator CLI",
)


def test_personal_greeting_lifecycle_across_clients(browser: Browser, tmp_path: Path):
    root = Path(__file__).resolve().parent.parent
    db_path = Path(os.environ["E2E_GREETING_DB_PATH"]).resolve()
    assert db_path != (root / "data/expenis.db").resolve()
    assert db_path.is_file()
    username = f"greeting-e2e-{time.time_ns()}"
    response = httpx.post(f"{API_BASE_URL}/api/register", json={
        "username": username, "password": "greeting-test-password",
    })
    response.raise_for_status()
    tokens = response.json()

    def command(*args: str, confirmation: str | None = None):
        env = {**os.environ, "EXPENIS_DB_PATH": str(db_path)}
        return subprocess.run(
            [sys.executable, "-m", "src.expenis.server", "greeting", *args],
            cwd=root, env=env, text=True, input=confirmation,
            capture_output=True, check=True,
        ).stdout

    def activate(page):
        page.bring_to_front()
        page.evaluate("() => document.querySelector('flt-semantics-placeholder')?.click()")
        expect_transactions_screen(page)

    def refresh(page):
        activate(page)
        with page.expect_response(lambda r: r.url.endswith("/api/me/greeting")):
            page.get_by_role("button", name=re.compile(r"^Refresh(?: Refresh)?$")).click()

    text = "Поздравляю с праздником! 🎉\nПусть всё получится!"
    command("set", "--username", username, "--text", text)
    contexts = [browser.new_context(
        base_url=os.environ["E2E_BASE_URL"], viewport={"width": 390, "height": 844},
    ) for _ in range(2)]
    try:
        pages = []
        storage = json.dumps({
            "flutter.access_token": tokens["access_token"],
            "flutter.refresh_token": tokens["refresh_token"],
            "flutter.username": username,
        })
        for context in contexts:
            # Set only once: subsequent reloads must retain actual auth state.
            context.add_init_script(f"""if (!localStorage.getItem('greeting-test-initialized')) {{
                const values = {storage};
                for (const [key, value] of Object.entries(values)) localStorage.setItem(key, JSON.stringify(value));
                localStorage.setItem('greeting-test-initialized', 'true');
            }}""")
            page = context.new_page()
            open_app(page)
            expect_transactions_screen(page)
            expect(page.get_by_text(text, exact=True)).to_be_visible()
            pages.append(page)
        a, b = pages
        activate(a)
        a.get_by_role("button", name="Close greeting").click()
        expect(a.get_by_text(text, exact=True)).to_have_count(0)
        refresh(b)
        expect(b.get_by_text(text, exact=True)).to_have_count(0)
        command("set", "--username", username, "--text", text)
        for page in pages:
            refresh(page)
            expect(page.get_by_text(text, exact=True)).to_be_visible()
        output = command("set", "--all", "--text", "Всем хорошего дня! 🎉", confirmation="yes\n")
        assert "Recipients: " in output
        for page in pages:
            refresh(page)
            expect(page.get_by_text("Всем хорошего дня! 🎉", exact=True)).to_be_visible()
        activate(a)
        open_section(a, "Accounts")
        expect(a.get_by_text("Всем хорошего дня! 🎉", exact=True)).to_have_count(0)
        open_section(a, "Transactions")
        expect(a.get_by_text("Всем хорошего дня! 🎉", exact=True)).to_be_visible()
        # HomeScreen animates tab changes for 250 ms; capture the settled layout.
        a.wait_for_timeout(350)
        a.screenshot(path=str(tmp_path / "personal-greeting-phone.png"))
        command("delete", "--all", confirmation="yes\n")
        for page in pages:
            refresh(page)
            expect(page.get_by_text("Всем хорошего дня! 🎉", exact=True)).to_have_count(0)
        a.route("**/api/me/greeting", lambda route: route.fulfill(status=503, json={"error": "test"}))
        refresh(a)
        expect(a.get_by_role("group", name=re.compile(r"Could not load greeting\."))).to_be_visible()
        expect(a.get_by_text("No transactions", exact=False)).to_be_visible()
        expect(a.get_by_role("button", name="Add transaction", exact=True)).to_be_enabled()
        expect_transactions_screen(a)
    except Exception:
        for index, context in enumerate(contexts):
            for page in context.pages:
                print(f"Client {index}: {page.locator('body').aria_snapshot()}")
                page.screenshot(path=str(tmp_path / f"failure-client-{index}.png"))
        raise
    finally:
        for context in contexts:
            context.close()
