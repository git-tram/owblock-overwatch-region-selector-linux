#!/usr/bin/env bash
set -euo pipefail

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "Please run as root: sudo $0" >&2
  exit 1
fi

rm -f /usr/local/bin/owblock
rm -f /usr/local/share/applications/owblock
rm -f /usr/local/share/icons/hicolor/256x256/apps/owblock.png
rm -rf /opt/owblock

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/local/share/applications >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q -t /usr/local/share/icons/hicolor >/dev/null 2>&1 || true
fi

echo "OWBlock uninstalled."