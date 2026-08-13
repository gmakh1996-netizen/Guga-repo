"""
E2E test: web player language-switching behaviour.

Verifies that clicking each locale switcher (KA / EN / RU) updates the player's
<iframe>/<video> `src` and that the new src carries the expected `lang` query
parameter. Results are written to `test_results.json` for assertion reporting.

Runs against YOUR OWN player. Set the target with BASE_URL / TEST_PATH env vars;
it defaults to a local dev server so it never points at a third-party site by
accident.

Usage:
    pip install playwright
    playwright install chromium
    BASE_URL=http://localhost:3000 TEST_PATH=/watch/test python tests/test_language_switch.py
"""

import json
import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# --- Configuration -----------------------------------------------------------
# Point these at your own player. BASE_URL defaults to a local dev server.
BASE_URL = os.environ.get("BASE_URL", "http://localhost:3000")
TEST_PATH = os.environ.get("TEST_PATH", "/watch/test")
HEADLESS = os.environ.get("HEADLESS", "1") != "0"
REPORT_PATH = os.environ.get("REPORT_PATH", "test_results.json")

# Locale -> (selector for the switcher button, expected query fragment).
# Adjust the selectors to match your real markup. These use accessible-name
# text matching first; swap for data-testid / CSS if your DOM differs, e.g.
#   "button": '[data-testid="lang-ka"]'
LOCALES = [
    {"code": "ka", "button": 'button:has-text("KA")', "expected": "lang=ka"},
    {"code": "en", "button": 'button:has-text("EN")', "expected": "lang=en"},
    {"code": "ru", "button": 'button:has-text("RU")', "expected": "lang=ru"},
]

# The player element whose `src` should change. Covers either an <iframe> or an
# HTML5 <video>. Narrow this if your page has more than one.
PLAYER_SELECTOR = "iframe, video"

# How long to wait for the src to change after a click (ms).
SRC_UPDATE_TIMEOUT = 5000


def read_player_src(page):
    """Return the current `src` of the player element, or None."""
    el = page.query_selector(PLAYER_SELECTOR)
    return el.get_attribute("src") if el else None


def run():
    target = f"{BASE_URL.rstrip('/')}{TEST_PATH}"
    results = {"target": target, "cases": []}
    all_passed = True

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()

        print(f"→ Loading {target}")
        page.goto(target, wait_until="domcontentloaded")

        # Ensure the player is present before we start switching.
        page.wait_for_selector(PLAYER_SELECTOR, timeout=SRC_UPDATE_TIMEOUT)
        previous_src = read_player_src(page)

        for loc in LOCALES:
            case = {
                "locale": loc["code"],
                "expected_fragment": loc["expected"],
                "detected_src": None,
                "passed": False,
                "error": None,
            }
            try:
                button = page.query_selector(loc["button"])
                if button is None:
                    raise AssertionError(f'switcher not found: {loc["button"]}')

                button.click()

                # Wait for the src to actually change from its previous value,
                # so we assert against the updated DOM rather than a stale read.
                try:
                    page.wait_for_function(
                        """([sel, prev]) => {
                            const el = document.querySelector(sel);
                            return el && el.getAttribute('src') && el.getAttribute('src') !== prev;
                        }""",
                        arg=[PLAYER_SELECTOR, previous_src],
                        timeout=SRC_UPDATE_TIMEOUT,
                    )
                except PWTimeout:
                    pass  # fall through; assertion below produces the real message

                current_src = read_player_src(page)
                case["detected_src"] = current_src

                assert current_src, "player has no src after switch"
                assert loc["expected"] in current_src, (
                    f'expected "{loc["expected"]}" in src, got: {current_src}'
                )

                case["passed"] = True
                previous_src = current_src
                print(f"  ✓ {loc['code']}: {current_src}")

            except AssertionError as e:
                case["error"] = str(e)
                all_passed = False
                print(f"  ✗ {loc['code']}: {e}")

            results["cases"].append(case)

        browser.close()

    results["passed"] = all_passed
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nReport written to {REPORT_PATH} — {'PASS' if all_passed else 'FAIL'}")

    return all_passed


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
