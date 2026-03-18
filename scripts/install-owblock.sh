#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "Please run as root: sudo $0" >&2
  exit 1
fi

APP_DIR="/opt/owblock"
BIN_DIR="/usr/local/bin"
DESKTOP_DIR="/usr/local/share/applications"
ICON_DIR="/usr/local/share/icons/hicolor/256x256/apps"

mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"

echo "[1/6] Installing application files"
install -m 644 "$ROOT/app/owblock.py" "$APP_DIR/owblock.py"
install -m 644 "$ROOT/app/owblock_gui.py" "$APP_DIR/owblock_gui.py"
install -m 644 "$ROOT/app/regions.json" "$APP_DIR/regions.json"
install -m 644 "$ROOT/app/requirements.txt" "$APP_DIR/requirements.txt"
install -m 644 "$ROOT/assets/owblock.png" "$APP_DIR/owblock.png"

echo "[2/6] Creating virtual environment"
python3 -m venv "$APP_DIR/.venv"

echo "[3/6] Installing Python dependencies"
"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip wheel setuptools
"$APP_DIR/.venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

echo "[4/6] Installing launcher"
install -m 755 "$ROOT/scripts/owblock" "$BIN_DIR/owblock"

echo "[5/6] Installing desktop file and icon"
install -m 644 "$ROOT/desktop/owblock.desktop" "$DESKTOP_DIR/owblock.desktop"
install -m 644 "$ROOT/assets/owblock.png" "$ICON_DIR/owblock.png"

echo "[6/6] Refreshing caches if available"
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q -t /usr/local/share/icons/hicolor >/dev/null 2>&1 || true
fi

cat <<'EOF'

Installed successfully.

Launch methods:
  - Menu entry: OWBlock (Admin)
  - Terminal: owblock

Installed paths:
  /opt/owblock/owblock.py
  /opt/owblock/owblock_gui.py
  /opt/owblock/regions.json
  /opt/owblock/owblock.png
  /opt/owblock/.venv/
  /usr/local/bin/owblock
  /usr/local/share/applications/owblock.desktop

EOF
