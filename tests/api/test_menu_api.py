"""API tests for GET /api/daily-menu (TEST_PLAN.md section 3.1)."""
import pytest

from models.menu_api import MenuApi

pytestmark = pytest.mark.api

EXPECTED_MENU = [
    "Margherita Pizza",
    "Pepperoni Pizza",
    "Quattro Stagioni",
    "Vegetarian Delight",
    "BBQ Chicken Pizza",
]


@pytest.mark.smoke
def test_daily_menu_returns_five_items(menu_api: MenuApi) -> None:
    """API-M1: 200, success: true, and 5 items."""
    response = menu_api.get_daily_menu()

    assert response.status == 200
    assert "application/json" in response.headers["content-type"]
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 5
    assert body["message"] == "Daily menu retrieved successfully"


def test_daily_menu_contains_expected_pizzas(menu_api: MenuApi) -> None:
    """API-M1 (content): the menu lists the 5 known pizzas, without duplicates."""
    names = [item.name for item in menu_api.get_menu_items()]

    assert sorted(names) == sorted(EXPECTED_MENU)


def test_every_menu_item_has_required_fields(menu_api: MenuApi) -> None:
    """API-M2: every item has non-empty name, description and imageUrl."""
    for item in menu_api.get_menu_items():
        for field, value in vars(item).items():
            assert isinstance(value, str) and value.strip(), (
                f"{item.name!r}: field {field!r} is missing or empty"
            )


@pytest.mark.parametrize("name", EXPECTED_MENU)
def test_menu_item_image_loads(menu_api: MenuApi, name: str) -> None:
    """API-M3: every imageUrl loads with 200 and an image content type."""
    item = next((i for i in menu_api.get_menu_items() if i.name == name), None)
    assert item is not None, f"{name!r} not found in the menu"

    response = menu_api.get_image(item.image_url)

    assert response.status == 200, f"{item.image_url} returned {response.status}"
    assert response.headers["content-type"].startswith("image/")
    assert len(response.body()) > 0
