from typing import Generator

import pytest
from playwright.sync_api import APIRequestContext, Playwright

from models.menu_api import MenuApi


@pytest.fixture(scope="session")
def api(playwright: Playwright, base_url: str) -> Generator[APIRequestContext, None, None]:
    """An APIRequestContext bound to the app's base URL."""
    context = playwright.request.new_context(base_url=base_url)
    try:
        response = context.get("/api/daily-menu")
    except Exception as exc:  # connection refused, DNS, etc.
        context.dispose()
        pytest.exit(f"App is not reachable at {base_url}: {exc}", returncode=1)
    if not response.ok:
        context.dispose()
        pytest.exit(f"App at {base_url} is unhealthy: {response.status}", returncode=1)
    yield context
    context.dispose()


@pytest.fixture
def menu_api(api: APIRequestContext) -> MenuApi:
    return MenuApi(api)
