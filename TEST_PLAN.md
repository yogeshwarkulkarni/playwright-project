# Test Plan: Awesome Pizza (http://localhost:3000)

## 1. What the application does

An Express app with a static frontend and a JSON API.

### Pages
| Page | Purpose |
|---|---|
| `/` (index.html) | Shows the daily menu, a cart with a name field, order placement, order lookup, and order status changes |
| `/login.html` | Staff login (the hint on the page says `user` / `pass`) |
| `/protected.html` | Staff-only area that shows secret recipes, staff discount, VIP code and delivery note |

All pages share a dark/light **theme toggle** (🌙/☀️). The choice is saved in `localStorage.theme`.

### Main page features
- **Menu**: loaded from `GET /api/daily-menu`. It returns 5 pizzas: Margherita, Pepperoni, Quattro Stagioni, Vegetarian Delight, BBQ Chicken. Each card has an image (with an SVG fallback if the image fails), a name, a description and −/+ quantity buttons.
- **Cart**: lists each item with its quantity and a **Remove** button, plus a "Total Items" counter. When empty it shows "Your cart is empty".
- **Place Order** button: enabled only when the cart has items **and** the name field is not blank. It sends `POST /api/orders`. On success it shows a toast "Order placed successfully! Order ID: …", clears the cart and name, fills in the Order ID field, and shows the order details.
- **Order lookup**: an Order ID field plus a **Look Up Order** button (Enter also works). It calls `GET /api/orders/:id`. Error toasts: "Please enter an order ID" and "Order not found: …".
- **Order details panel**: shows ID, Customer, a Status badge and the items. Which actions appear depends on status:
  - `RECEIVED`: **Mark as Delivering**, **Cancel Order**
  - `DELIVERING`: **Mark as Delivered**
  - `DELIVERED` / `CANCELED`: no actions
- **Notifications**: a `#notification` toast with a `success` or `error` class that hides after 3 seconds.

### Login and protected area
- Login sends `POST /api/login` and saves the returned token in `localStorage.auth_token`, then redirects to `/protected.html`. Bad credentials show "Invalid username or password". Pressing Enter in the password field submits.
- If you are already logged in, opening `/login.html` redirects to `/protected.html`.
- `/protected.html` with no token shows "This page is only visible to logged-in users" and a link to log in. The Logout button stays hidden and no data loads.
- `/protected.html` with a token calls `GET /api/protected` with `Authorization: Bearer <token>` and shows 4 data cards. A 401 response removes the token and redirects to login.
- **Logout** removes the token and redirects to `/login.html`.

### API (as observed)
| Method and path | Behaviour |
|---|---|
| `GET /api/daily-menu` | 200, `{success, data:[{name, description, imageUrl}], message}` |
| `POST /api/orders` | 201 on success. Returns an ID like `order-<timestamp>-<rand>` and status `RECEIVED`. Returns 400 if `sender` is missing or blank, if `contents` is missing or empty, or if `quantity` is ≤ 0 |
| `GET /api/orders/:id` | 200, or 404 with "Order with ID 'x' not found" |
| `PUT /api/orders/:id` | Body `{status}`. Status must be one of RECEIVED, DELIVERING, DELIVERED, CANCELED, otherwise 400. Returns 404 for an unknown ID |
| `POST /api/login` | Returns `{success:true, token}` for user/pass. Returns `{success:false, error:"Invalid credentials"}` otherwise |
| `GET /api/protected` | 401 "Valid token required" without a valid token |
| `GET /api/orders` | 404 (there is no endpoint that lists orders) |

### Possible defects found during exploration
These are worth tests. Each test should be marked `xfail` or flagged until someone confirms the intended behaviour.
1. **Any status change is allowed by the API.** `DELIVERED → DELIVERING → RECEIVED`, `CANCELED` after `DELIVERED`, and similar changes all succeed. The UI only offers valid next steps, but the server does not enforce them.
2. **Unknown menu items are accepted.** `POST /api/orders` accepted `{"name":"Nope"}`.
3. **Fractional quantities are accepted** (`quantity: 1.5`).
4. **The token is static and can be forged.** The token is `base64({"role":"admin"})`. Anyone can create it, and it never changes or expires.
5. **Possible XSS.** The customer name, item names and protected data are inserted with `innerHTML` and are not escaped. The inline `onclick="updateQuantity('${item.name}')"` also breaks if a name contains `'`.
6. **The theme toggle does nothing on the protected page when logged out.** Its click handler is only attached after the token check passes.
7. **No upper limit on quantity**, and no limit on the length of the name.

> Note: the API keeps state between requests (orders stay on the server). Each test should create the orders it needs, preferably through the API, and must not depend on other tests' data.

## 2. Approach and tooling

- **Stack**: the existing `pytest` + `pytest-playwright` setup (Chromium, trace kept on failure).
- **Configuration**: set `base_url = http://localhost:3000` in `pytest.ini` (or with `--base-url`) so tests can use `page.goto("/")`.
- **Layers**:
  - **API tests** use Playwright's `APIRequestContext` (the `playwright.request` fixture). They are fast and check the server contract and validation.
  - **UI end-to-end tests** cover user flows in the browser.
  - **Hybrid**: set up data through the API, then check it in the UI (for example, create an order through the API and look it up in the UI).
- **Locators**: prefer `get_by_role`, `get_by_label` and `get_by_text`. Use IDs (`#cart-items`, `#notification`) only where there are no accessible names.
- **Isolation**: each test gets a fresh browser context (default). Clear `localStorage` where auth or theme state matters.
- **Network mocking** (`page.route`) to test error handling: menu API failure, a 500 when placing an order, the server being unreachable, and a broken image falling back to the SVG.

### Suggested layout
```
tests/
  conftest.py              # base_url, api_context, create_order helper, logged_in_page fixture
  api/
    test_menu_api.py
    test_orders_api.py
    test_auth_api.py
  ui/
    test_menu.py
    test_cart.py
    test_place_order.py
    test_order_lookup.py
    test_order_status.py
    test_login.py
    test_protected.py
    test_theme.py
  pages/                   # optional page objects: HomePage, LoginPage, ProtectedPage
```
`tests/test_example.py` (which tests playwright.dev) should be removed once the real suite is in place.

### Markers
`@pytest.mark.smoke`, `api`, `ui`, `security`, `known_bug` (xfail). Register them in `pytest.ini`.

## 3. Test cases

Priority: **P1** = critical path or smoke, **P2** = important, **P3** = edge cases or nice to have.

### 3.1 API: Menu (`test_menu_api.py`)
| ID | Case | Pri |
|---|---|---|
| API-M1 | `GET /api/daily-menu` returns 200, `success: true`, and 5 items | P1 |
| API-M2 | Every item has non-empty `name`, `description` and `imageUrl` | P2 |
| API-M3 | Every `imageUrl` loads (200, image content type) | P3 |

### 3.2 API: Orders (`test_orders_api.py`)
| ID | Case | Pri |
|---|---|---|
| API-O1 | Creating a valid order returns 201, an ID matching `order-\d+-\d+`, status `RECEIVED`, and the same sender and contents that were sent | P1 |
| API-O2 | `GET /api/orders/:id` returns the order that was created | P1 |
| API-O3 | `GET` with an unknown ID returns 404 and the expected message | P2 |
| API-O4 | POST validation (parametrized): missing sender, empty sender, whitespace-only sender, missing contents, `contents: []`, quantity 0, negative quantity, non-numeric quantity: each returns 400 with the right message | P1 |
| API-O5 | PUT for each valid status returns 200 and the status is saved (confirm with a GET) | P1 |
| API-O6 | PUT with an invalid status returns 400 and the list of allowed statuses | P2 |
| API-O7 | PUT on an unknown ID returns 404 | P2 |
| API-O8 | `known_bug`: changing status from a final state (DELIVERED or CANCELED) should be rejected | P2 |
| API-O9 | `known_bug`: an item name not on the menu should be rejected | P3 |
| API-O10 | `known_bug`: a fractional quantity should be rejected | P3 |
| API-O11 | A malformed JSON body or a missing Content-Type returns 400, not 500 | P3 |

### 3.3 API: Auth (`test_auth_api.py`)
| ID | Case | Pri |
|---|---|---|
| API-A1 | `user`/`pass` returns `success: true` and a non-empty token | P1 |
| API-A2 | Wrong password, wrong username, empty fields or a missing body give `success: false` | P1 |
| API-A3 | `/api/protected` returns 401 with no header, a malformed header or a garbage token | P1 |
| API-A4 | `/api/protected` with a valid token returns 200 with `secretRecipes`, `staffDiscount`, `vipCode` and `deliveryNote` | P1 |
| API-A5 | `security`/`known_bug`: a hand-made `base64({"role":"admin"})` token should **not** be accepted, and tokens should be different for each login | P2 |

### 3.4 UI: Menu (`test_menu.py`)
| ID | Case | Pri |
|---|---|---|
| UI-M1 | The page title is "Awesome Pizza - Order Online", and the header and the "Today's Menu" heading are visible | P1 |
| UI-M2 | 5 menu cards are shown with names and descriptions that match the API | P1 |
| UI-M3 | Each card shows its quantity as 0 at first | P2 |
| UI-M4 | A broken image falls back to the "Pizza Image" SVG (route the image request to return 404) | P3 |
| UI-M5 | If the menu API returns `success:false`, the "Failed to load menu" toast appears. If the request fails at the network level, the "Error loading menu" toast appears | P2 |

### 3.5 UI: Cart (`test_cart.py`)
| ID | Case | Pri |
|---|---|---|
| UI-C1 | At first the cart shows "Your cart is empty", Total Items is 0, and Place Order is disabled | P1 |
| UI-C2 | Clicking + adds the item to the cart with quantity 1, and the card's counter updates | P1 |
| UI-C3 | Clicking + several times on several items gives the right quantity per item and the right total | P1 |
| UI-C4 | Clicking − lowers the quantity. At 0 the item is removed from the cart | P2 |
| UI-C5 | Clicking − when the quantity is 0 has no effect and never shows a negative number | P2 |
| UI-C6 | The Remove button deletes the item, resets the card's counter to 0 and updates the total | P2 |
| UI-C7 | Removing the last item brings back the empty state | P2 |
| UI-C8 | The cart is not kept after a page reload (document whether that is intended) | P3 |

### 3.6 UI: Place Order (`test_place_order.py`)
| ID | Case | Pri |
|---|---|---|
| UI-P1 | Place Order is enabled only when there is a name **and** at least one item (check all 4 combinations) | P1 |
| UI-P2 | A name of only spaces keeps the button disabled | P2 |
| UI-P3 | **Happy path (smoke)**: add items, enter a name, place the order. Check the success toast and its ID, that the cart and name are cleared, that the Order ID field is filled in, and that the details panel shows the right customer, items and `RECEIVED` status | P1 |
| UI-P4 | The POST request body has the expected `sender` and `contents` (check with `page.expect_request`) | P2 |
| UI-P5 | A server error (mocked `success:false`) shows "Failed to place order: …" and the cart is kept | P2 |
| UI-P6 | A network failure (mocked abort) shows "Error placing order" | P3 |
| UI-P7 | `security`/`known_bug`: a name like `<img src=x onerror=…>` is shown as text and the script does not run | P2 |

### 3.7 UI: Order Lookup (`test_order_lookup.py`)
| ID | Case | Pri |
|---|---|---|
| UI-L1 | Looking up an order created through the API shows the details panel with the right data and the "Order found" toast | P1 |
| UI-L2 | Pressing Enter in the Order ID field also looks up the order | P2 |
| UI-L3 | An empty ID shows the "Please enter an order ID" toast | P2 |
| UI-L4 | An unknown ID shows the "Order not found: …" toast and hides the panel (also when a previous lookup was showing it) | P2 |
| UI-L5 | Spaces around the ID are trimmed | P3 |

### 3.8 UI: Order Status (`test_order_status.py`)
| ID | Case | Pri |
|---|---|---|
| UI-S1 | A `RECEIVED` order shows the Mark as Delivering and Cancel Order buttons | P1 |
| UI-S2 | RECEIVED → Mark as Delivering: the badge changes to DELIVERING, only Mark as Delivered remains, and a toast appears | P1 |
| UI-S3 | DELIVERING → Mark as Delivered: the badge changes to DELIVERED and no action buttons remain | P1 |
| UI-S4 | RECEIVED → Cancel Order: the badge changes to CANCELED and no action buttons remain | P1 |
| UI-S5 | The status is saved: a new lookup or a reload followed by a lookup shows the updated status | P2 |
| UI-S6 | Each status badge has the right CSS class (`status-received` and so on) | P3 |
| UI-S7 | A failed status update (mocked) shows "Failed to update order: …" | P3 |

### 3.9 UI: Login (`test_login.py`)
| ID | Case | Pri |
|---|---|---|
| UI-A1 | The Login link on the main page goes to `/login.html` | P2 |
| UI-A2 | Logging in with valid credentials redirects to `/protected.html` and saves `auth_token` in localStorage | P1 |
| UI-A3 | Invalid credentials show "Invalid username or password", the page stays on login, and no token is saved | P1 |
| UI-A4 | Empty fields show the error | P2 |
| UI-A5 | Pressing Enter in the password field submits the form | P2 |
| UI-A6 | The error message goes away when you try again | P3 |
| UI-A7 | Opening `/login.html` while logged in redirects to `/protected.html` | P2 |
| UI-A8 | If the server cannot be reached (mocked), the page shows "Login failed — server unreachable" | P3 |
| UI-A9 | The password field has `type=password` | P3 |

### 3.10 UI: Protected area (`test_protected.py`)
| ID | Case | Pri |
|---|---|---|
| UI-PR1 | Without a token, the page shows the auth-required message and a "Log in" link, the Logout button is hidden, and no data cards appear | P1 |
| UI-PR2 | With a token, the page shows all 4 cards (Secret Recipes with 3 items, Staff Discount, VIP Code, Delivery Note) and the Logout button | P1 |
| UI-PR3 | Logout removes the token and redirects to login. Going back to `/protected.html` shows the auth-required message again | P1 |
| UI-PR4 | An invalid token in localStorage (the API returns 401) is removed and the page redirects to login | P2 |
| UI-PR5 | The "Log in" link goes to the login page | P3 |
| UI-PR6 | If the protected API fails, the page shows "Failed to load protected data." | P3 |

### 3.11 UI: Theme (`test_theme.py`)
| ID | Case | Pri |
|---|---|---|
| UI-T1 | Clicking the toggle sets `data-theme="dark"` on `<html>`, changes the icon to ☀️ and sets `localStorage.theme=dark`. Clicking again switches back to light and 🌙 | P2 |
| UI-T2 | The dark theme is still on after a reload and on other pages (index → login → protected) | P2 |
| UI-T3 | The toggle works on the login page | P3 |
| UI-T4 | `known_bug`: the toggle should work on `/protected.html` when logged out | P3 |
| UI-T5 | Optional: compare screenshots in light and dark mode for the main page | P3 |

### 3.12 Cross-cutting (optional or later)
- **Accessibility**: run an axe-core scan on each page. The − and + buttons have no accessible names that say which pizza they belong to.
- **Responsive**: check the layout on a mobile viewport (iPhone emulation): the menu grid wraps and there is no horizontal scrolling.
- **Cross-browser**: run the P1 set on Firefox and WebKit.
- **Console errors**: fail UI tests on uncaught page errors (`page.on("pageerror")`).

## 4. Fixtures and helpers (conftest.py)
- `base_url`: `http://localhost:3000`
- `api` (session scope): an `APIRequestContext` bound to `base_url`
- `create_order(sender, contents, status=None)`: creates an order through the API and optionally sets its status. Returns the order dict.
- `auth_token`: logs in through the API and returns the token
- `logged_in_page`: puts the token in localStorage with `context.add_init_script` and opens `/protected.html`
- `home_page`: opens `/` and waits until 5 `.menu-item` cards are rendered

## 5. Execution
- Requirement: the app is running at `localhost:3000` before the tests start. Optionally, add a session fixture that checks `/api/daily-menu` and skips the run with a clear message if the app is down.
- Smoke run: `pytest -m smoke`
- Full run: `pytest`
- Parallel run: `pytest -n auto` (add `pytest-xdist`). This is safe because every test creates its own orders.
- Debugging: traces are already kept on failure (`--tracing retain-on-failure`). Use `playwright show-trace`.

## 6. Order of implementation
1. `conftest.py`, `base_url` and markers
2. The P1 API tests (menu, orders, auth)
3. The P1 UI smoke flows: menu loads, add to cart, place order, look up order, status changes, login/protected/logout
4. The P2 validation, negative and mocked error cases
5. The `known_bug` and security tests, P3 cases and cross-cutting checks

## 7. Out of scope
- Load and performance testing
- Server code and unit tests (only the HTTP interface is tested here)
- Payment, pricing and delivery logic (the app does not have them)
