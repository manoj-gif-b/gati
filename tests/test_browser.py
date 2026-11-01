import os
import subprocess
import sys
import time

import pytest

# Try importing playwright.sync_api; skip only if it raises ImportError.
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
    PLAYWRIGHT_IMPORT_ERROR = ""
except ImportError as exc:
    PLAYWRIGHT_AVAILABLE = False
    PLAYWRIGHT_IMPORT_ERROR = str(exc)

RUN_BROWSER_TESTS = os.environ.get("RUN_BROWSER_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_BROWSER_TESTS,
    reason="browser tests skipped unless RUN_BROWSER_TESTS=1",
)

BASE_URL = "http://127.0.0.1:8000"


def _server_reachable():
    import urllib.request
    try:
        urllib.request.urlopen(BASE_URL + "/", timeout=2)
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def browser_server():
    if _server_reachable():
        yield
        return

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for _ in range(30):
        if _server_reachable():
            break
        time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError("uvicorn did not start in time")
    yield
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="session")
def playwright_browser(browser_server):
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip(
            "playwright not installed: " + PLAYWRIGHT_IMPORT_ERROR
        )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(playwright_browser):
    context = playwright_browser.new_context()
    page = context.new_page()
    yield page
    context.close()


def test_demo_five_steps(page):
    # Step 1: pick a student and start.
    page.goto(BASE_URL)
    page.wait_for_selector("#student-picker", timeout=10000)
    # Wait until the dropdown is populated from GET /api/students (no fixed wait).
    page.wait_for_function(
        "() => document.querySelector('#student-picker').options.length > 0",
        timeout=10000,
    )
    # Pick the first student from the populated dropdown (value comes from the API).
    page.select_option("#student-picker", value="1")
    page.click("#start-btn")

    # Learn screen shows concept card and reason.
    page.wait_for_selector("#learn-card:not(.hidden)", timeout=10000)
    assert page.is_visible("#learn-skill-title")
    assert page.is_visible("#learn-reason")
    assert page.is_visible("#learn-concept")

    # Step 2: Continue to Solve.
    page.click("#learn-continue")
    page.wait_for_selector("#solve-card:not(.hidden)", timeout=10000)

    # Answer one question wrong.
    page.wait_for_selector("#solve-options button", timeout=10000)
    page.click("#solve-options button:last-child")
    # Wait until feedback text is set by the server (no fixed wait).
    page.wait_for_function(
        "() => document.querySelector('#solve-feedback').textContent.trim().length > 0",
        timeout=10000,
    )
    feedback = page.text_content("#solve-feedback")
    assert feedback in ("Correct!", "Incorrect.")

    # Revisit / next-step reason is visible.
    page.wait_for_function(
        "() => document.querySelector('#solve-next-reason').textContent.trim().length > 0",
        timeout=10000,
    )
    reason = page.text_content("#solve-next-reason")
    assert len(reason) > 0

    # Continue.
    page.click("#solve-continue")

    # Step 4: answer correctly until mastery reaches ~95% (test check appears).
    max_attempts = 40
    for _ in range(max_attempts):
        if page.is_visible("#learn-card:not(.hidden)"):
            page.click("#learn-continue")
            page.wait_for_selector("#solve-card:not(.hidden)", timeout=10000)

        if not page.is_visible("#solve-card:not(.hidden)"):
            break

        page.wait_for_selector("#solve-options button", timeout=10000)
        page.click("#solve-options button:first-child")
        # Wait until feedback text is set by the server (no fixed wait).
        page.wait_for_function(
            "() => document.querySelector('#solve-feedback').textContent.trim().length > 0",
            timeout=10000,
        )

        pct_text = page.text_content("#solve-mastery-pct")
        pct = int(pct_text.replace("%", "").strip()) if pct_text else 0

        # If the mastery check already appeared (test_required), we are on the
        # test screen and there is nothing to continue on the solve screen.
        if page.is_visible("#test-card:not(.hidden)"):
            break

        page.click("#solve-continue")

        if pct >= 95:
            break

    # Step 5: check that the test screen appears automatically.
    page.wait_for_selector("#test-card:not(.hidden)", timeout=15000)
    assert page.is_visible("#test-card")

    # Complete the 3-question check.
    for _ in range(3):
        page.wait_for_selector("#test-options button", timeout=10000)
        page.click("#test-options button:first-child")
        # Advance to the next question (or show the submit button on the last one).
        page.wait_for_selector("#test-continue:not(.hidden)", timeout=10000)
        page.click("#test-continue")

    submit_btn = page.locator("button", has_text="Submit Mastery Check")
    submit_btn.click()
    # Wait until test feedback text is set by the server (no fixed wait).
    page.wait_for_function(
        "() => document.querySelector('#test-feedback').textContent.trim().length > 0",
        timeout=10000,
    )
    feedback = page.text_content("#test-feedback")
    assert "PASSED" in feedback or "NOT PASSED" in feedback
