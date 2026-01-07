#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
APP_NAME="Cheeses HVAC Control Deck"
PRODUCT_NAME="CheesesHVACControlDeck"
BUILD_DIR="$ROOT_DIR/build"
APP_DIR="$BUILD_DIR/${APP_NAME}.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
PYTHON_DIR="$RESOURCES_DIR/python"
VENV_DIR="$RESOURCES_DIR/venv"
ICON_SOURCE="$ROOT_DIR/Assets/AppIcon.png"

mkdir -p "$BUILD_DIR"
rm -rf "$APP_DIR"
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR" "$PYTHON_DIR"

pushd "$ROOT_DIR" >/dev/null
swift build -c release
popd >/dev/null

BIN_PATH="$ROOT_DIR/.build/release/$PRODUCT_NAME"
if [[ ! -f "$BIN_PATH" ]]; then
  echo "Binary not found at $BIN_PATH" >&2
  exit 1
fi

cp "$BIN_PATH" "$MACOS_DIR/$PRODUCT_NAME"
chmod +x "$MACOS_DIR/$PRODUCT_NAME"

cp "$ROOT_DIR/Info.plist" "$CONTENTS_DIR/Info.plist"

# Bundle the Python package + web assets.
cp -R "$ROOT_DIR/../redlink_controller" "$PYTHON_DIR/"
cp -R "$ROOT_DIR/../web" "$PYTHON_DIR/"
cp "$ROOT_DIR/../config.example.json" "$PYTHON_DIR/config.example.json"

# Create a venv with dependencies for the bundled server.
if command -v python3 >/dev/null 2>&1; then
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
  "$VENV_DIR/bin/pip" install -r "$ROOT_DIR/../requirements.txt"
else
  echo "Warning: python3 not found. The app may not start the server." >&2
fi

if [[ -f "$ICON_SOURCE" ]]; then
  ICONSET_DIR="$BUILD_DIR/AppIcon.iconset"
  TMP_ICON="$BUILD_DIR/AppIcon-square.png"
  rm -rf "$ICONSET_DIR"
  mkdir -p "$ICONSET_DIR"

  WIDTH=$(sips -g pixelWidth "$ICON_SOURCE" | awk '/pixelWidth/ {print $2}')
  HEIGHT=$(sips -g pixelHeight "$ICON_SOURCE" | awk '/pixelHeight/ {print $2}')
  if [[ -n "$WIDTH" && -n "$HEIGHT" ]]; then
    if [[ "$WIDTH" -lt "$HEIGHT" ]]; then
      SIZE="$WIDTH"
    else
      SIZE="$HEIGHT"
    fi
    sips -c "$SIZE" "$SIZE" "$ICON_SOURCE" --out "$TMP_ICON" >/dev/null
  else
    cp "$ICON_SOURCE" "$TMP_ICON"
  fi

  for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$TMP_ICON" --out "$ICONSET_DIR/icon_${size}x${size}.png" >/dev/null
    sips -z "$((size * 2))" "$((size * 2))" "$TMP_ICON" --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" >/dev/null
  done

  iconutil -c icns "$ICONSET_DIR" -o "$RESOURCES_DIR/AppIcon.icns"
  rm -rf "$ICONSET_DIR" "$TMP_ICON"
else
  echo "Warning: $ICON_SOURCE not found. App icon will be missing." >&2
fi

echo "Built $APP_DIR"
