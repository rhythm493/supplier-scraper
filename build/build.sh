#!/usr/bin/env bash
#
# Build Supplier Scraper for Linux
#
# Usage:
#   ./build/build.sh                  # Build bundle only
#   ./build/build.sh --deb            # Build bundle + Debian package
#   ./build/build.sh --clean          # Clean + build
#
# Output in dist/:
#   SupplierScraper/          — one-directory PyInstaller bundle
#   SupplierScraper.tar.gz    — compressed archive
#   SupplierScraper.deb       — Debian package (with --deb)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$PROJECT_DIR/dist"
BUILD_DIR="$SCRIPT_DIR"

BUILD_DEB=false
CLEAN=false
for arg in "$@"; do
    case "$arg" in
        --deb) BUILD_DEB=true ;;
        --clean) CLEAN=true ;;
    esac
done

cd "$PROJECT_DIR"

echo "=== Supplier Scraper — Linux Build ==="
echo "Project: $PROJECT_DIR"
echo ""

# Step 1: Verify Python environment
if [ ! -f ".venv/bin/activate" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller and build dependencies..."
    pip install pyinstaller
fi

# Step 2: Clean previous builds
if [ "$CLEAN" = true ]; then
    echo "Cleaning previous builds..."
    rm -rf "$DIST_DIR/SupplierScraper" "$BUILD_DIR/build"
fi

# Step 3: Install patchright browser
echo ""
echo "=== Installing patchright browser (chrome) ==="
python -m patchright install chrome

# Step 4: Run PyInstaller
echo ""
echo "=== Building with PyInstaller ==="
pyinstaller "$BUILD_DIR/scraper.spec" --clean --noconfirm

echo ""
echo "=== Build complete ==="
echo "Bundle: $DIST_DIR/SupplierScraper/"

# Step 5: Create tar.gz archive
echo ""
echo "=== Creating tar.gz archive ==="
cd "$DIST_DIR"
tar czf SupplierScraper.tar.gz SupplierScraper/
echo "Archive: $DIST_DIR/SupplierScraper.tar.gz"
cd "$PROJECT_DIR"

# Step 6: Create Debian package (optional)
if [ "$BUILD_DEB" = true ]; then
    if ! command -v dpkg-deb &>/dev/null; then
        echo "dpkg-deb not found. Install: apt install dpkg-dev"
        echo "Skipping Debian package."
        exit 0
    fi

    echo ""
    echo "=== Creating Debian package ==="

    PKG_DIR=$(mktemp -d)/supplier-scraper
    mkdir -p "$PKG_DIR/DEBIAN"
    mkdir -p "$PKG_DIR/opt/supplier-scraper"
    mkdir -p "$PKG_DIR/usr/share/applications"
    mkdir -p "$PKG_DIR/usr/share/icons/hicolor/256x256/apps"

    # Copy bundle contents
    cp -r "$DIST_DIR/SupplierScraper/"* "$PKG_DIR/opt/supplier-scraper/"

    # .desktop entry
    cat > "$PKG_DIR/usr/share/applications/supplier-scraper.desktop" <<'DESKTOP'
[Desktop Entry]
Name=Supplier Scraper
Comment=Google-based supplier and manufacturer data scraper
Exec=/opt/supplier-scraper/SupplierScraper
Type=Application
Terminal=true
Categories=Office;DataVisualization;
Icon=supplier-scraper
DESKTOP

    # Minimal 256x256 PNG icon (blue square)
    python3 -c "
import struct, zlib
size = 256
buf = b''
for y in range(size):
    buf += b'\\x00'
    for x in range(size):
        r, g, b, a = (41, 128, 185, 255)
        buf += struct.pack('BBBB', r, g, b, a)
def chunk(c, d):
    return struct.pack('>I', len(d)) + c + d + struct.pack('>I', zlib.crc32(c + d) & 0xffffffff)
ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
idat = chunk(b'IDAT', zlib.compress(buf))
iend = chunk(b'IEND', b'')
with open('$PKG_DIR/usr/share/icons/hicolor/256x256/apps/supplier-scraper.png', 'wb') as f:
    f.write(b'\\x89PNG\\r\\n\\x1a\\n' + ihdr + idat + iend)
"

    # Debian control
    cat > "$PKG_DIR/DEBIAN/control" <<CONTROL
Package: supplier-scraper
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Depends: libc6 (>= 2.31), libx11-6, libxcb1, libxkbcommon0 (>= 0.5.0),
 libgtk-3-0 (>= 3.24), libnss3 (>= 2:3.49), libnspr4 (>= 4.25),
 libdbus-1-3 (>= 1.12), libatk-bridge2.0-0 (>= 2.34),
 libcups2 (>= 2.3), libdrm2 (>= 2.4), libgbm1 (>= 20.0),
 libasound2 (>= 1.2), ca-certificates, xdg-utils
Maintainer: Supplier Scraper Team
Description: Google-based supplier and medical device manufacturer scraper
 Extracts supplier and manufacturer data from Google Search results
 with automated website visits and Excel export.
CONTROL

    # postinst
    cat > "$PKG_DIR/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e
chmod +x /opt/supplier-scraper/SupplierScraper
update-desktop-database 2>/dev/null || true
exit 0
POSTINST
    chmod 755 "$PKG_DIR/DEBIAN/postinst"

    # Build
    dpkg-deb --build "$PKG_DIR"
    mv "${PKG_DIR}.deb" "$DIST_DIR/SupplierScraper.deb"
    rm -rf "$(dirname "$PKG_DIR")"

    echo "Debian package: $DIST_DIR/SupplierScraper.deb"
fi

echo ""
echo "=== All done ==="
echo "  Bundle:     $DIST_DIR/SupplierScraper/"
echo "  Archive:    $DIST_DIR/SupplierScraper.tar.gz"
if [ -f "$DIST_DIR/SupplierScraper.deb" ]; then
    echo "  Debian pkg: $DIST_DIR/SupplierScraper.deb"
fi
