# Nuty Image Converter

A lightweight Nautilus (GNOME Files) extension that adds **Convert Image** and **Compress Image** options to the right-click menu, allowing quick image format conversion and compression directly from your file manager.

---

## Features

- **Convert Image** — right-click any image and convert to common formats (PNG, JPG, WebP, AVIF, HEIC, GIF, TIFF, BMP, ICO, JXL, PSD, PDF)
- **Compress Image** — re-encode images with quality presets (Lossless, High Quality 85%, Medium Quality 65%, Low Quality 35%)
- **Smart format detection** — available formats are dynamically discovered from ImageMagick; only supported formats appear in the menu
- **Fallback encoders** — if ImageMagick fails, falls back to avifenc, cwebp, heif-enc, or ffmpeg automatically
- **Keep Both / Replace Original** — dialog after conversion lets you choose whether to keep the original file
- **Progress dialog** — shows conversion progress with a pulse bar

---

## Requirements

- GNOME + Nautilus
- Python 3
- ImageMagick (`magick` or `convert`)

---

## Installation

Clone the repository:

```bash
git clone https://github.com/witherdotexe/nuttyimgconverter.git
cd nuttyimgconverter
```

Make the installer executable and run it:

```bash
chmod +x install.sh
./install.sh
```

If root permissions are required:

```bash
sudo ./install.sh
```

---

## Optional Tools

Install additional encoders for improved format support:

```bash
chmod +x install-tools.sh
./install-tools.sh
```

---

## Uninstall

```bash
chmod +x uninstall.sh
./uninstall.sh
```

---

## Restart Nautilus

After installing or uninstalling:

```bash
nautilus -q
```

---

## Usage

1. Open Nautilus.
2. Right-click an image file.
3. Select **Convert Image** and pick a target format, or **Compress Image** and pick a quality preset.
4. After conversion, choose **Keep Both** or **Replace Original**.

---

## Showcase


https://github.com/user-attachments/assets/565e005e-f1cc-4bf5-87f1-d7434d736ff5


<img width="501" height="386" alt="Screenshot From 2026-06-10 23-42-19" src="https://github.com/user-attachments/assets/57dcb233-1281-4559-baf3-0ba3632d86e1" />

<img width="480" height="607" alt="Screenshot From 2026-06-10 23-42-09" src="https://github.com/user-attachments/assets/d3a0b96b-584b-49dd-ad85-81c0d2554afd" />

<img width="421" height="106" alt="Screenshot From 2026-06-10 23-44-00" src="https://github.com/user-attachments/assets/4f3dd6a1-56e4-4625-9da0-e86e04b6d67c" />

<img width="511" height="105" alt="Screenshot From 2026-06-10 23-43-35" src="https://github.com/user-attachments/assets/2bd4cb72-32d9-4b98-8c45-27c2b50256ae" />
---

## Changelog

### Improvements in this fork
- Added **Compress Image** submenu with 4 quality presets (Lossless, High 85%, Medium 65%, Low 35%)
- Made format detection dynamic — queries ImageMagick at runtime instead of a hardcoded list
- Expanded output formats to 13 common ones (PNG, JPG, WebP, AVIF, HEIC, GIF, TIFF, BMP, ICO, JXL, PSD, PDF)
- Added lossy PNG compression via color palette reduction for real file size savings
- AVIF/HEIC/WebP now appear in menu if standalone tools (avifenc, heif-enc, cwebp) are installed
- ImageMagick's `format:` prefix is now used explicitly to prevent format guessing errors
- Return code is now validated after ImageMagick runs to catch silent failures

### Bugs fixed
- `install.sh` and `install-tools.sh` no longer crash on distros where `/etc/os-release` omits `ID_LIKE`
- Temp files now use the correct extension (e.g., `photo_tmp.jpg` instead of `photo.jpg.tmp`) so fallback encoders detect the format properly
- Same-format check now canonicalizes input extension without blocking valid conversions

---

## License

This project is licensed under the GNU General Public License (GPL). See the LICENSE file for details.
