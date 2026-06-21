#!/usr/bin/env bash
set -euo pipefail

# Install the Nautilus Python extension (image_converter.py) to the user's Nautilus extensions directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/nautilus-python/extensions"

mkdir -p "$EXT_DIR"

src="$SCRIPT_DIR/image_converter.py"
if [ ! -f "$src" ]; then
  echo "error: $src not found. Run this script from the extension directory where image_converter.py lives." >&2
  exit 2
fi

cp -f "$src" "$EXT_DIR/"

# Make gi.require_version for Nautilus tolerant to multiple versions (4.1 then 4.0)
python3 - "$EXT_DIR/image_converter.py" <<'PY'
import sys, re
p = sys.argv[1]
s = open(p, 'r', encoding='utf-8').read()
# replace first occurrence only
s_new = re.sub(r"gi.require_version\(\s*\"Nautilus\",\s*\"[0-9.]+\"\s*\)",
               "try:\n    gi.require_version(\"Nautilus\", \"4.1\")\nexcept Exception:\n    try:\n        gi.require_version(\"Nautilus\", \"4.0\")\n    except Exception:\n        pass",
               s, count=1)
open(p, 'w', encoding='utf-8').write(s_new)
print('patched require_version in', p)
PY

# Syntax check
if python3 -m py_compile "$EXT_DIR/image_converter.py"; then
  echo "Installation OK -> $EXT_DIR/image_converter.py"
else
  echo "Python syntax check failed" >&2
  exit 3
fi

# Try to install system dependencies for Nautilus Python extensions
if [ -f /etc/os-release ]; then
  . /etc/os-release
  id=${ID,,}
  id_like="${ID_LIKE:-}"
  id_like="${id_like,,}"
else
  id=""
  id_like=""
fi

install_pkgs=()
if command -v apt >/dev/null 2>&1 || command -v apt-get >/dev/null 2>&1; then
  install_pkgs=(python3-nautilus python3-gi gir1.2-nautilus-3.0 gir1.2-notify-0.7)
  echo "Detected Debian-like distro. Installing: ${install_pkgs[*]}"
  sudo apt update && sudo apt install -y "${install_pkgs[@]}" || echo "apt install failed; please install packages manually: ${install_pkgs[*]}"
elif command -v dnf >/dev/null 2>&1; then
  install_pkgs=(nautilus-python python3-gobject python3-gobject-base libnotify)
  echo "Detected Fedora-like distro. Installing: ${install_pkgs[*]}"
  sudo dnf install -y "${install_pkgs[@]}" || echo "dnf install failed; please install packages manually: ${install_pkgs[*]}"
elif command -v pacman >/dev/null 2>&1; then
  install_pkgs=(python-nautilus python-gobject libnotify)
  echo "Detected Arch-like distro. Installing: ${install_pkgs[*]}"
  sudo pacman -Syu --noconfirm "${install_pkgs[@]}" || echo "pacman install failed; please install packages manually: ${install_pkgs[*]}"
elif command -v zypper >/dev/null 2>&1; then
  install_pkgs=(python3-nautilus python3-gobject libnotify-gtk3)
  echo "Detected openSUSE. Installing: ${install_pkgs[*]}"
  sudo zypper install -y "${install_pkgs[@]}" || echo "zypper install failed; please install packages manually: ${install_pkgs[*]}"
else
  echo "Could not detect package manager. Ensure the system has python3-nautilus (or nautilus-python), python3-gi and libnotify installed." >&2
fi

# Restart Nautilus to pick up the extension
if command -v nautilus >/dev/null 2>&1; then
  echo "Restarting Nautilus..."
  nautilus -q || true
fi

echo "Done."
