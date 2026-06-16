#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# pdf-extract.sh  –  Build (if needed) and run PDF Text Extractor
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAR="$SCRIPT_DIR/target/pdf-text-extractor-1.0.0.jar"

# Build if the fat JAR does not exist yet
if [ ! -f "$JAR" ]; then
    echo "JAR not found — building with Maven..."
    cd "$SCRIPT_DIR"
    mvn -q package -DskipTests
    echo "Build complete."
fi

exec java -jar "$JAR" "$@"
