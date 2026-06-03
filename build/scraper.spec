# PyInstaller spec for Supplier Scraper
#
# Build with (from project root):
#   pyinstaller build/scraper.spec
#
# Output: dist/SupplierScraper.exe  (onefile bundle)
#

import os
import re

import patchright as _patchright
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

root = os.getcwd()

# Inject version from env (set by CI from git tag)
injected_version = os.environ.get("VERSION", "")
if injected_version:
    init_py = os.path.join(root, "scraper", "__init__.py")
    with open(init_py) as f:
        content = f.read()
    content = re.sub(r'__version__\s*=\s*"[^"]*"', f'__version__ = "{injected_version}"', content)
    with open(init_py, "w") as f:
        f.write(content)

_patchright_dir = os.path.dirname(_patchright.__file__)

a = Analysis(
    [os.path.join(root, "run_scraper.py")],
    pathex=[root],
    binaries=[],
    datas=collect_data_files("nicegui", include_py_files=True)
    + collect_data_files("fastapi"),
    hiddenimports=[
        "scraper",
        "scraper.browser",
        "scraper.config",
        "scraper.dedup",
        "scraper.extractors",
        "scraper.pipeline",
        "scraper.runner",
        "scraper.search",
        "scraper.session",
        "scraper.types",
        "scraper.updater",
        "scraper.validators",
        "scraper.llm_extractor",
        "llama_cpp",
        "huggingface_hub",
        "huggingface_hub.file_download",
        "packaging",
        "gui",
        "gui.state",
        "gui.main",
        "gui.pages",
        "gui.pages.config",
        "gui.pages.run",
        "gui.pages.history",
        "gui.pages.help",
        "gui.history",
        "patchright",
        "patchright.sync_api",
        "patchright._impl",
        "bs4",
        "bs4.builder._lxml",
        "lxml",
        "openpyxl",
        "openpyxl.cell._writer",
        "nicegui",
        "nicegui.themes",
        "fastapi",
        "uvicorn",
        "pydantic",
        "websockets",
        "libaiofile",
        "libpyee",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["gi", "gi.repository", "tkinter", "test"],
    noarchive=False,
    optimize=0,
)

# Include patchright driver directory (node binary + JS package)
_driver_dir = os.path.join(_patchright_dir, "driver")
if os.path.isdir(_driver_dir):
    for _root, _dirs, _files in os.walk(_driver_dir):
        for _f in _files:
            _src = os.path.join(_root, _f)
            _dst = os.path.join("patchright", "driver", os.path.relpath(_root, _driver_dir), _f)
            a.datas.append((_dst, _src, "DATA"))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    exclude_binaries=False,
    name="SupplierScraper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)
