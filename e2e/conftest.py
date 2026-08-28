import logging
import os

import pytest

os.environ.setdefault("E2E_BASE_URL", "http://127.0.0.1:8080")
os.environ.setdefault("E2E_API_URL", "http://127.0.0.1:8000")

logger = logging.getLogger("e2e")


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict) -> dict:
    return {
        **browser_type_launch_args,
        "channel": "chrome",
        "headless": True,
    }


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    return {
        **browser_context_args,
        "base_url": os.environ["E2E_BASE_URL"],
    }


@pytest.fixture(autouse=True)
def _log_test(request: pytest.FixtureRequest):
    logger.info("start %s", request.node.name)
    yield
    logger.info("end %s", request.node.name)


@pytest.fixture
def page(page):
    page.set_default_timeout(15_000)

    def _on_console(msg) -> None:
        if msg.type in ("error", "warning"):
            logger.info("browser %s: %s", msg.type, msg.text)

    page.on("console", _on_console)
    page.on("pageerror", lambda err: logger.info("pageerror: %s", err))
    return page
