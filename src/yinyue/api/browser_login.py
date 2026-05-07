"""
Browser-based NetEase Cloud Music login using Playwright.
Launches a real Chromium window pointing to the official NetEase login page.
User scans QR on the official site, Playwright detects login and saves cookies.
"""
import json
import sys
import time
from pathlib import Path


def do_browser_login(cookie_file: str) -> bool:
    """Open browser, wait for user to log into NetEase, save cookies to file.

    Returns True if login was detected within 3 minutes.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--window-size=480,720", "--window-position=100,100"],
        )
        context = browser.new_context()
        page = context.new_page()

        # Go directly to the NetEase login page (shows QR code by default)
        page.goto("https://music.163.com/#/login/", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # NetEase login page redirects to /#/login?redirect_url=..., keep polling
        # Click the QR login tab if needed (the page defaults to QR usually)
        for _ in range(180):  # 3 minutes
            time.sleep(1)
            cookies = context.cookies()
            music_u = next(
                (c for c in cookies if c["name"] == "MUSIC_U" and c["value"]),
                None,
            )
            if music_u:
                cookie_str = "; ".join(
                    f"{c['name']}={c['value']}" for c in cookies
                )
                Path(cookie_file).write_text(cookie_str, encoding="utf-8")
                browser.close()
                return True

        browser.close()
        return False


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "cookies.txt"
    ok = do_browser_login(output)
    print("SUCCESS" if ok else "TIMEOUT")
    sys.exit(0 if ok else 1)
