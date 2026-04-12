#!/bin/bash
# ─────────────────────────────────────────────────────────
#  Build Todo Manager as a standalone macOS .app
#  Usage:  chmod +x build_mac.sh && ./build_mac.sh
# ─────────────────────────────────────────────────────────

set -e

APP_NAME="Todo Manager"
DIST_DIR="dist"

echo "=== Todo Manager — macOS Build ==="

# 1. Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install from https://python.org"
    exit 1
fi
PYTHON=$(command -v python3)
echo "Python: $PYTHON ($(python3 --version))"

# 2. Create / activate virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

# 3. Install py2app
echo "Installing py2app..."
pip install --quiet --upgrade pip
pip install --quiet py2app

# 4. Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# 5. Build the app
echo "Building $APP_NAME.app ..."
python setup.py py2app 2>&1 | tail -20

# 6. Confirm
if [ -d "$DIST_DIR/$APP_NAME.app" ]; then
    SIZE=$(du -sh "$DIST_DIR/$APP_NAME.app" | cut -f1)
    echo ""
    echo "✅  Build successful!"
    echo "    Location : $DIST_DIR/$APP_NAME.app"
    echo "    Size     : $SIZE"
    echo ""
    echo "Run it:"
    echo "    open \"$DIST_DIR/$APP_NAME.app\""
    echo ""
    echo "Or move to /Applications:"
    echo "    cp -r \"$DIST_DIR/$APP_NAME.app\" /Applications/"
else
    echo "❌  Build failed — check output above."
    exit 1
fi

deactivate
