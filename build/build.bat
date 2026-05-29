@echo off
REM Build Supplier Scraper for Windows
REM
REM Usage:
REM   build\build.bat
REM
REM Output in dist\:
REM   SupplierScraper\          - one-directory PyInstaller bundle
REM   SupplierScraper.exe       - standalone executable
REM

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..\
set DIST_DIR=%PROJECT_DIR%dist
set BUILD_DIR=%SCRIPT_DIR%

echo === Supplier Scraper - Windows Build ===
echo Project: %PROJECT_DIR%
echo.

cd /d "%PROJECT_DIR%"

REM Step 1: Check Python and PyInstaller
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python not found. Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Step 2: Clean previous builds
if exist "%DIST_DIR%\SupplierScraper" (
    echo Cleaning previous build...
    rmdir /s /q "%DIST_DIR%\SupplierScraper"
)
if exist "%BUILD_DIR%\build" rmdir /s /q "%BUILD_DIR%\build"

REM Step 3: Install patchright browser (Chrome for Testing)
echo.
echo === Installing patchright browser (chrome) ===
python -m patchright install chrome

REM Step 4: Run PyInstaller
echo.
echo === Building with PyInstaller ===
pyinstaller "%BUILD_DIR%\scraper.spec" --clean --noconfirm

echo.
echo === Build complete ===
echo Bundle: %DIST_DIR%\SupplierScraper\
echo Binary: %DIST_DIR%\SupplierScraper\SupplierScraper.exe

REM Step 5: Copy standalone binary to dist root
echo.
echo === Copying standalone binary ===
copy "%DIST_DIR%\SupplierScraper\SupplierScraper.exe" "%DIST_DIR%\SupplierScraper.exe"

echo.
echo === All done ===
echo   Bundle:  %DIST_DIR%\SupplierScraper\
echo   Binary:  %DIST_DIR%\SupplierScraper.exe

pause
