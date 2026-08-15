import os
import shutil
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger("hsbot.browser.diagnostics")

def run_browser_diagnostics() -> dict:
    chrome_status = "NOT FOUND"
    selenium_status = "FAILED"
    driver_status = "FAILED"
    error_details = []

    # 1. Verify Chrome
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chrome",
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_status = "FOUND"
            break
    
    if chrome_status == "NOT FOUND":
        if shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("google-chrome-stable"):
            chrome_status = "FOUND"

    # 2. Verify Selenium package
    try:
        import selenium
        selenium_status = "READY"
    except Exception as e:
        error_details.append(f"Selenium import failed: {e}")

    # 3. Verify ChromeDriver / Selenium Manager
    if selenium_status == "READY":
        try:
            opts = Options()
            opts.add_argument("--headless")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            
            # Start a brief headless driver session to verify capability
            driver = webdriver.Chrome(options=opts)
            driver.quit()
            driver_status = "READY"
        except Exception as e:
            error_details.append(f"ChromeDriver failed to start: {e}")

    # Format the report string as requested in Section 6
    report_text = (
        "BROWSER:\n"
        f"Chrome: {chrome_status}\n"
        f"Selenium: {selenium_status}\n"
        f"Driver: {driver_status}"
    )

    return {
        "chrome": chrome_status,
        "selenium": selenium_status,
        "driver": driver_status,
        "report": report_text,
        "errors": " | ".join(error_details) if error_details else None
    }


async def run_simple_google_test() -> dict:
    """Runs the Section 7 simple Selenium test: open Google, verify process/title."""
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=opts)
        driver.get("https://www.google.com")
        
        # Verify page parameters
        title = driver.title
        current_url = driver.current_url
        
        driver.quit()
        return {
            "success": True,
            "tool": "browser_open",
            "url": current_url,
            "title": title,
            "error": None
        }
    except Exception as e:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return {
            "success": False,
            "tool": "browser_open",
            "error": f"Chrome could not be started or navigated: {str(e)}"
        }
