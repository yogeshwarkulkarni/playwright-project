"""Object model for the Daily Menu API.

Follows the Page Object Model pattern (https://playwright.dev/python/docs/pom),
applied to the API layer: it wraps a Playwright ``APIRequestContext``, keeps the
endpoint paths in one place, and gives tests a higher-level API to call.
"""
from dataclasses import dataclass

from playwright.sync_api import APIRequestContext, APIResponse


@dataclass(frozen=True)
class MenuItem:
    name: str
    description: str
    image_url: str

    @classmethod
    def from_json(cls, data: dict) -> "MenuItem":
        return cls(
            name=data.get("name"),
            description=data.get("description"),
            image_url=data.get("imageUrl"),
        )


class MenuApi:
    DAILY_MENU_PATH = "/api/daily-menu"

    def __init__(self, request: APIRequestContext) -> None:
        self.request = request

    def get_daily_menu(self) -> APIResponse:
        """Send ``GET /api/daily-menu`` and return the raw response."""
        return self.request.get(self.DAILY_MENU_PATH)

    def get_menu_items(self) -> list[MenuItem]:
        """Fetch the daily menu and return its items as ``MenuItem`` objects."""
        response = self.get_daily_menu()
        assert response.ok, f"Menu request failed: {response.status} {response.text()}"
        return [MenuItem.from_json(item) for item in response.json()["data"]]

    def get_image(self, image_url: str) -> APIResponse:
        """Fetch a menu item's image. ``imageUrl`` is relative to the site root."""
        return self.request.get("/" + image_url.lstrip("/"))
