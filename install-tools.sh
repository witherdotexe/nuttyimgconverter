#!/usr/bin/env bash
set -euo pipefail

# Installs optional encoder tools used as fallbacks by the extension.
# Supported tools: avifenc (libavif), cwebp (libwebp), heif-enc (libheif), ffmpeg, imagemagick
# Usage: sudo ./install-tools.sh or ./install-tools.sh --dry-run

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
fi

install_cmd=""
pkgs=()

if [ -f /etc/os-release ]; then
  . /etc/os-release
  id=${ID,,}
  id_like="${ID_LIKE:-}"
  id_like="${id_like,,}"
else
  id=""
  id_like=""
fi

case "${id}" in
  ubuntu|debian|linuxmint)
    pkgman="apt"
    pkgs=(imagemagick libavif-bin webp libheif-examples ffmpeg)
    ;;
  fedora)
    pkgman="dnf"
    pkgs=(ImageMagick libavif libwebp-tools libheif ffmpeg)
    ;;
  arch|manjaro)
    pkgman="pacman"
    pkgs=(imagemagick libavif libwebp libheif ffmpeg)
    ;;
  opensuse*|suse)
    pkgman="zypper"
    pkgs=(ImageMagick libavif-tools libwebp-tools libheif ffmpeg)
    ;;
  *)
    # Try ID_LIKE
    if echo "$id_like" | grep -q debian; then
      pkgman="apt"
      pkgs=(imagemagick libavif-bin webp libheif-examples ffmpeg)
    elif echo "$id_like" | grep -q rhel; then
      pkgman="dnf"
    pkgs=(ImageMagick libavif-tools libwebp-tools libheif-tools ffmpeg)
    else
      echo "Unsupported distro: $id. Please install: imagemagick, libavif (avifenc), webp (cwebp), libheif (heif-enc), ffmpeg" >&2
      exit 1
    fi
    ;;
esac

echo "Detected package manager: $pkgman"
if [ $DRY_RUN -eq 1 ]; then
  echo "Would install: ${pkgs[*]}"
  exit 0
fi

case "$pkgman" in
  apt)
    sudo apt update
    sudo apt install -y "${pkgs[@]}"
    ;;
  dnf)
    sudo dnf install -y "${pkgs[@]}"
    ;;
  pacman)
    sudo pacman -Syu --noconfirm "${pkgs[@]}"
    ;;
  zypper)
    sudo zypper install -y "${pkgs[@]}"
    ;;
  *)
    echo "Unhandled package manager: $pkgman" >&2
    exit 2
    ;;
esac

echo "Installation finished. Verify tools:"
for t in magick avifenc cwebp heif-enc ffmpeg; do
  if command -v "$t" >/dev/null 2>&1; then
    echo " - $t: OK ($(command -v $t))"
  else
    echo " - $t: MISSING"
  fi
done

echo "Note: package names vary between distributions. If a package failed to install, install the corresponding encoder manually (avifenc, cwebp, heif-enc, ffmpeg)."
