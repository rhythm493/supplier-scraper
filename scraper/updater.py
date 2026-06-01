from __future__ import annotations

import logging
import os
import platform
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
from packaging.version import Version

from scraper import __version__

REPO = "anomalyco/ORO"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
TIMEOUT = 15

log = logging.getLogger(__name__)


@dataclass
class UpdateInfo:
    available: bool = False
    latest_version: str = ""
    current_version: str = __version__
    download_url: str = ""
    release_url: str = ""
    asset_name: str = ""
    size: int = 0
    error: str = ""


def _normalize_tag(tag: str) -> str:
    return tag.removeprefix("v")


def _platform_asset_suffix() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "windows.exe"
    if system == "linux":
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return "linux-x86_64.AppImage"
        return f"linux-{machine}.AppImage"
    if system == "darwin":
        return "macos.dmg"
    return system


def check_for_update(
    on_progress: Callable[[str], None] | None = None,
) -> UpdateInfo:
    info = UpdateInfo()

    try:
        if on_progress:
            on_progress("Checking for updates...")

        resp = requests.get(API_URL, timeout=TIMEOUT, headers={"Accept": "application/vnd.github.v3+json"})
        if resp.status_code == 403:
            info.error = "Rate limited by GitHub API. Try again later."
            return info
        if resp.status_code == 404:
            info.error = "No releases found."
            return info
        resp.raise_for_status()

        data = resp.json()
        latest_tag = data.get("tag_name", "")
        if not latest_tag:
            info.error = "No version tag found."
            return info

        latest_ver = _normalize_tag(latest_tag)
        current_ver = _normalize_tag(__version__)

        try:
            is_newer = Version(latest_ver) > Version(current_ver)
        except Exception:
            is_newer = latest_ver != current_ver and latest_ver > current_ver

        suffix = _platform_asset_suffix()

        asset = None
        for a in data.get("assets", []):
            name: str = a.get("name", "")
            if name.endswith(suffix) or suffix in name:
                asset = a
                break

        if not asset and not is_newer:
            asset = data["assets"][0] if data.get("assets") else None

        info.latest_version = latest_ver
        info.release_url = data.get("html_url", f"https://github.com/{REPO}/releases/tag/{latest_tag}")

        if not is_newer:
            return info

        if not asset:
            if on_progress:
                on_progress(f"Update v{latest_ver} available — no platform asset found for {suffix}")
            info.available = True
            return info

        info.available = True
        info.download_url = asset["browser_download_url"]
        info.asset_name = asset["name"]
        info.size = asset.get("size", 0)

        if on_progress:
            size_mb = info.size / 1_048_576
            on_progress(f"Update v{latest_ver} available ({info.asset_name}, {size_mb:.1f} MB)")

    except requests.RequestException as e:
        info.error = f"Network error: {e}"
    except Exception as e:
        info.error = f"Unexpected error: {e}"

    return info


def download_update(
    url: str,
    on_progress: Callable[[int, int], None] | None = None,
) -> Path | None:
    try:
        resp = requests.get(url, stream=True, timeout=TIMEOUT)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        suffix = Path(urlparse(url).path).suffix or ".exe"
        tmp = Path(tempfile.mktemp(suffix=suffix))

        downloaded = 0
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if on_progress and total:
                    on_progress(downloaded, total)

        return tmp

    except Exception as e:
        log.error("Download failed: %s", e)
        return None


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _app_path() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve()
    return Path(sys.argv[0]).resolve()


def apply_update(downloaded: Path) -> bool:
    system = platform.system().lower()

    try:
        if system == "windows":
            return _apply_windows(downloaded)
        if system == "linux":
            return _apply_linux(downloaded)
        if system == "darwin":
            return _apply_macos(downloaded)
        log.warning("Unsupported platform: %s", system)
        return False
    except Exception as e:
        log.error("Update failed: %s", e)
        return False


def _apply_windows(downloaded: Path) -> bool:
    target = _app_path().parent / downloaded.name
    try:
        os.replace(downloaded, target)
        log.info("Replaced binary: %s", target)
        return True
    except PermissionError:
        old = _app_path().with_name(_app_path().name + ".old")
        try:
            _app_path().rename(old)
            os.replace(downloaded, _app_path())
            old.unlink(missing_ok=True)
            log.info("Replaced running binary via rename trick")
            return True
        except Exception:
            log.warning("Permission denied — update will apply on next restart via installer")
            _launch_installer(downloaded)
            return True


def _launch_installer(installer: Path) -> None:
    import subprocess

    try:
        if platform.system().lower() == "windows":
            subprocess.Popen(
                [str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                shell=False,
            )
        elif platform.system().lower() == "linux" and str(installer).endswith(".AppImage"):
            os.chmod(installer, 0o755)
            subprocess.Popen([str(installer), "--no-sandbox"], shell=False)
    except Exception as e:
        log.error("Failed to launch installer: %s", e)


def _apply_linux(downloaded: Path) -> bool:
    target = _app_path()
    try:
        downloaded.chmod(0o755)
        os.replace(downloaded, target)
        log.info("Replaced binary: %s", target)
        return True
    except PermissionError:
        old = target.with_name(target.name + ".old")
        target.rename(old)
        downloaded.chmod(0o755)
        os.replace(downloaded, target)
        old.unlink(missing_ok=True)
        return True


def _apply_macos(downloaded: Path) -> bool:
    return _apply_linux(downloaded)
