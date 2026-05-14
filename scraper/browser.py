from __future__ import annotations

import io
import json
import logging
import os
import platform
import subprocess
import urllib.request
import zipfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selenium.webdriver import Chrome

logger = logging.getLogger(__name__)

_CFT_API = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CFT_CACHE = os.path.join(_PROJECT_DIR, "chrome-cache")


def _find_chrome_binary() -> str | None:
    system = platform.system()

    if system == "Windows":
        candidates = [
            "./chrome-win64/chrome.exe",
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return _which("chrome.exe")

    if system == "Linux":
        local_path = "./chrome-linux64/chrome"
        if os.path.exists(local_path):
            return local_path
        for name in ("google-chrome", "chromium-browser", "chromium"):
            found = _which(name)
            if found:
                return found
        snap_path = "/snap/bin/chromium"
        if os.path.exists(snap_path):
            return snap_path
        flatpak_path = "/var/lib/flatpak/exports/bin/com.google.Chrome"
        if os.path.exists(flatpak_path):
            return flatpak_path
        return None

    if system == "Darwin":
        local_path = "./chrome-mac/Google Chrome.app/Contents/MacOS/Google Chrome"
        local_path2 = "./chrome-mac/Chromium.app/Contents/MacOS/Chromium"
        for path in (local_path, local_path2):
            if os.path.exists(path):
                return path
        mac_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(mac_path):
            return mac_path
        for name in ("google-chrome", "chromium", "chromium-browser"):
            found = _which(name)
            if found:
                return found
        return None

    return None


def _which(name: str) -> str | None:
    system = platform.system()
    cmd = "where" if system == "Windows" else "which"
    try:
        result = subprocess.run([cmd, name], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            path = result.stdout.strip().splitlines()[0]
            return path
    except Exception:
        pass
    return None


def _find_chromedriver() -> str | None:
    system = platform.system()
    extensions = {"Windows": ".exe"}
    ext = extensions.get(system, "")

    local_path = f"./chromedriver{ext}"
    if os.path.exists(local_path):
        return os.path.abspath(local_path)

    return _which(f"chromedriver{ext}")


def _cft_platform() -> str:
    s = platform.system()
    if s == "Linux":
        return "linux64"
    if s == "Windows":
        return "win64"
    if s == "Darwin":
        return "mac-arm64" if platform.machine() in ("arm64", "aarch64") else "mac-x64"
    msg = f"Unsupported platform: {s}"
    raise RuntimeError(msg)


def _ensure_cft() -> tuple[str | None, str | None]:
    cache_dir = _CFT_CACHE
    plat = _cft_platform()
    info = _fetch_cft_info()
    version = info["version"]
    base = os.path.join(cache_dir, plat, version)
    driver_name = _os_chromedriver_name()

    chrome_bin = _find_cft_chrome(base, plat)
    driver_bin = os.path.join(base, f"chromedriver-{plat}", driver_name)

    if chrome_bin and os.path.exists(driver_bin):
        return chrome_bin, driver_bin

    os.makedirs(os.path.join(cache_dir, plat, version), exist_ok=True)

    if not chrome_bin:
        url = _cft_download_url(info["downloads"]["chrome"], plat)
        _download_zip(url, base)
        chrome_bin = _find_cft_chrome(base, plat)

    if not os.path.exists(driver_bin):
        url = _cft_download_url(info["downloads"]["chromedriver"], plat)
        _download_zip(url, base)

    return chrome_bin, driver_bin if os.path.exists(driver_bin) else None


def _fetch_cft_info() -> dict:
    resp = urllib.request.urlopen(_CFT_API, timeout=30)
    return json.loads(resp.read().decode())["channels"]["Stable"]


def _cft_download_url(downloads: list, plat: str) -> str:
    for entry in downloads:
        if entry["platform"] == plat:
            return entry["url"]
    msg = f"No CfT download for platform {plat}"
    raise RuntimeError(msg)


def _download_zip(url: str, target: str) -> None:
    logger.info("Downloading Chrome for Testing: %s", url)
    resp = urllib.request.urlopen(url, timeout=300)
    data = resp.read()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(target)
    logger.info("Extracted to %s", target)


def _find_cft_chrome(base: str, plat: str) -> str | None:
    s = platform.system()
    if s == "Windows":
        candidates = [os.path.join(base, "chrome-win64", "chrome.exe")]
    elif s == "Linux":
        candidates = [os.path.join(base, "chrome-linux64", "chrome")]
    elif s == "Darwin":
        candidates = [
            os.path.join(
                base, "chrome-mac", "Google Chrome for Testing.app", "Contents", "MacOS", "Google Chrome for Testing"
            ),
            os.path.join(base, "chrome-mac", "Chromium.app", "Contents", "MacOS", "Chromium"),
        ]
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)
    return None


def _os_chromedriver_name() -> str:
    return f"chromedriver{'.exe' if platform.system() == 'Windows' else ''}"


def setup_driver(
    use_undetected: bool = True,
    page_load_timeout: int = 25,
) -> Chrome:
    chrome_path = _find_chrome_binary()
    driver_path = _find_chromedriver()

    if chrome_path is None:
        logger.info("Chrome not found locally — downloading Chrome for Testing")
        cft_chrome, cft_driver = _ensure_cft()
        if cft_chrome is None:
            logger.warning("Chrome for Testing download failed, proceeding without binary_location")
        else:
            chrome_path = cft_chrome
            if driver_path is None and cft_driver:
                driver_path = cft_driver

    if use_undetected:
        try:
            return _setup_undetected(chrome_path, driver_path, page_load_timeout)
        except Exception as e:
            logger.warning("Undetected ChromeDriver failed (%s), falling back to regular driver", e)

    return _setup_regular(chrome_path, driver_path, page_load_timeout, use_undetected=False)


def _setup_undetected(
    chrome_path: str | None,
    driver_path: str | None,
    timeout: int,
) -> Chrome:
    import undetected_chromedriver as uc  # type: ignore[import-untyped]

    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")

    if chrome_path and os.path.exists(chrome_path):
        options.binary_location = chrome_path

    driver: Chrome = uc.Chrome(
        options=options,
        driver_executable_path=driver_path if driver_path and os.path.exists(driver_path) else None,
        use_subprocess=True,
    )
    driver.set_page_load_timeout(timeout)
    return driver


def _setup_regular(
    chrome_path: str | None,
    driver_path: str | None,
    timeout: int,
    use_undetected: bool = False,
) -> Chrome:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option(
        "prefs",
        {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "plugins.always_open_pdf_externally": True,
        },
    )

    if chrome_path and os.path.exists(chrome_path):
        options.binary_location = chrome_path

    if use_undetected:
        raise RuntimeError("Regular driver requested but use_undetected=True")

    if driver_path and os.path.exists(driver_path):
        service = Service(driver_path)
        driver: Chrome = webdriver.Chrome(service=service, options=options)  # type: ignore[no-redef, call-arg]
    else:
        service = Service(ChromeDriverManager().install())
        driver: Chrome = webdriver.Chrome(service=service, options=options)  # type: ignore[no-redef, call-arg]

    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: function() { return [1, 2, 3, 4, 5]; }})")
    driver.execute_script(
        "Object.defineProperty(navigator, 'languages', {get: function() { return ['en-US', 'en']; }})"
    )

    driver.set_page_load_timeout(timeout)
    return driver
