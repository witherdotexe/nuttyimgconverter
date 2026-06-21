import gi

gi.require_version("Nautilus", "4.1")
gi.require_version("Notify", "0.7")
gi.require_version("Gtk", "4.0")

import os
import shutil
import subprocess
import threading
import time

from gi.repository import GLib, GObject, Gtk, Nautilus, Notify

try:
    Notify.init("ImageConverter")
except Exception:
    pass


class ProgressDialog(Gtk.ApplicationWindow):
    """GTK progress dialog for image conversion."""

    def __init__(self, filename, format_to):
        super().__init__()
        self.set_title(f"Converting {filename}")
        self.set_default_size(450, 160)
        self.set_deletable(False)
        self.callback = None

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)

        file_label = Gtk.Label()
        file_label.set_markup(f"<b>Converting:</b> {filename}")
        file_label.set_halign(Gtk.Align.START)
        vbox.append(file_label)

        format_label = Gtk.Label()
        format_label.set_markup(f"<b>To format:</b> {format_to.upper()}")
        format_label.set_halign(Gtk.Align.START)
        vbox.append(format_label)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(False)
        self.progress_bar.pulse()
        vbox.append(self.progress_bar)

        self.status_label = Gtk.Label()
        self.status_label.set_text("Converting... Please wait")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_wrap(True)
        vbox.append(self.status_label)

        self.button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.button_box.set_halign(Gtk.Align.END)

        self.keep_both_btn = Gtk.Button(label="Keep Both")
        self.keep_both_btn.connect("clicked", self._on_keep_both)
        self.button_box.append(self.keep_both_btn)

        self.replace_btn = Gtk.Button(label="Replace Original")
        self.replace_btn.connect("clicked", self._on_replace)
        self.button_box.append(self.replace_btn)

        self.button_box.set_visible(False)
        vbox.append(self.button_box)

        self.set_child(vbox)
        self.present()

        GLib.timeout_add(100, self._animate_progress)

    def _animate_progress(self):
        """Animate progress bar during conversion."""
        if self.progress_bar and not self.button_box.get_visible():
            self.progress_bar.pulse()
            return True
        return False

    def _on_keep_both(self, button):
        """User wants to keep both files."""
        if self.callback:
            self.callback("keep_both")
        self.close()

    def _on_replace(self, button):
        """User wants to replace original."""
        if self.callback:
            self.callback("replace")
        self.close()

    def finish(self):
        """Show completion and choice buttons."""
        self.progress_bar.set_fraction(1.0)
        self.status_label.set_text("Conversion complete! What would you like to do?")
        self.button_box.set_visible(True)


class ImageConverterExtension(GObject.GObject, Nautilus.MenuProvider):
    def _find_magick(self):
        for name in ("magick", "convert"):
            path = shutil.which(name)
            if path:
                return path
        return None

    def _notify(self, title, message):
        try:
            n = Notify.Notification.new(title, message)
            n.show()
        except Exception:
            pass

    def _safe_output_path(self, path, ext):
        base = os.path.splitext(path)[0]
        return f"{base}.{ext}"

    def _finalize_conversion(self, src, tmp, final, title, message, dialog=None):
        """Move tmp to final, ask user about original file."""
        try:
            if not os.path.exists(tmp):
                self._notify(
                    "Conversion failed",
                    f"{os.path.basename(src)}: temporary output missing",
                )
                return

            if dialog and os.path.abspath(final) != os.path.abspath(src):

                def on_choice(choice):
                    try:
                        if choice == "replace":
                            os.replace(tmp, final)
                            try:
                                os.remove(src)
                            except:
                                pass
                            self._notify(title, message)
                        elif choice == "keep_both":
                            os.replace(tmp, final)
                            self._notify(title, f"{message} (Original kept)")
                    except Exception as e:
                        self._notify("Error", f"Could not finalize: {e}")

                dialog.callback = on_choice
            else:
                os.replace(tmp, final)
                if os.path.abspath(final) != os.path.abspath(src):
                    try:
                        os.remove(src)
                    except:
                        pass
                self._notify(title, message)
        except Exception as e:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            self._notify("Conversion failed", f"{os.path.basename(src)}: {e}")

    def _convert_file(self, magick_bin, fileinfo, ext, dialog=None):
        path = fileinfo.get_location().get_path()
        if not path:
            return

        try:
            mime = fileinfo.get_mime_type()
        except Exception:
            mime = None

        if mime and not mime.startswith("image/"):
            return

        final_output = self._safe_output_path(path, ext)
        tmp_output = f"{os.path.splitext(final_output)[0]}_tmp.{ext}"

        src_ext = os.path.splitext(path)[1].lower().lstrip(".")
        if src_ext == "jpeg":
            src_ext = "jpg"
        if src_ext == ext:
            self._notify(
                "Warning: Same format",
                f"{os.path.basename(path)} is already .{ext}; conversion skipped.",
            )
            if dialog:
                GLib.idle_add(dialog.close)
            return

        if not dialog:
            filename = os.path.basename(path)
            dialog = ProgressDialog(filename, ext)

        cmd = [magick_bin, path, "-strip"]
        if ext in ("jpg", "jpeg"):
            cmd.extend(["-quality", "75"])
        elif ext == "webp":
            cmd.extend(["-quality", "70"])
        elif ext == "avif":
            cmd.extend(["-quality", "65"])
        elif ext == "heic":
            cmd.extend(["-quality", "75"])
        elif ext == "png":
            cmd.extend(["-define", "png:compression-level=1"])
        cmd.append(f"{ext}:{tmp_output}")

        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            process.wait()

            if process.returncode != 0 or not os.path.exists(tmp_output):
                raise subprocess.CalledProcessError(
                    process.returncode, cmd, output="Output file not created"
                )

            GLib.idle_add(dialog.finish)
            self._finalize_conversion(
                path,
                tmp_output,
                final_output,
                "Image Converted",
                f"{os.path.basename(path)} → {os.path.basename(final_output)}",
                dialog,
            )
            return
        except subprocess.CalledProcessError as e:
            if ext == "avif" and shutil.which("avifenc"):
                try:
                    avif_cmd = [
                        "avifenc",
                        "--min",
                        "0",
                        "--max",
                        "65",
                        "-s",
                        "10",
                        path,
                        tmp_output,
                    ]
                    subprocess.run(
                        avif_cmd,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    GLib.idle_add(dialog.finish)
                    self._finalize_conversion(
                        path,
                        tmp_output,
                        final_output,
                        "Image Converted (avifenc)",
                        f"{os.path.basename(path)} → {os.path.basename(final_output)}",
                        dialog,
                    )
                    return
                except subprocess.CalledProcessError:
                    pass

            if ext == "webp" and shutil.which("cwebp"):
                try:
                    cwebp_cmd = ["cwebp", "-q", "70", "-m", "6", path, "-o", tmp_output]
                    subprocess.run(
                        cwebp_cmd,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    GLib.idle_add(dialog.finish)
                    self._finalize_conversion(
                        path,
                        tmp_output,
                        final_output,
                        "Image Converted (cwebp)",
                        f"{os.path.basename(path)} → {os.path.basename(final_output)}",
                        dialog,
                    )
                    return
                except subprocess.CalledProcessError:
                    pass

            if ext == "heic" and shutil.which("heif-enc"):
                try:
                    heif_cmd = ["heif-enc", path, tmp_output]
                    subprocess.run(
                        heif_cmd,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    GLib.idle_add(dialog.finish)
                    self._finalize_conversion(
                        path,
                        tmp_output,
                        final_output,
                        "Image Converted (heif-enc)",
                        f"{os.path.basename(path)} → {os.path.basename(final_output)}",
                        dialog,
                    )
                    return
                except subprocess.CalledProcessError:
                    pass

            if shutil.which("ffmpeg"):
                try:
                    ff_cmd = ["ffmpeg", "-y", "-i", path]
                    if ext in ("jpg", "jpeg"):
                        ff_cmd += ["-q:v", "1", tmp_output]
                    elif ext == "png":
                        ff_cmd += ["-compression_level", "0", tmp_output]
                    else:
                        ff_cmd += [tmp_output]
                    subprocess.run(
                        ff_cmd,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    GLib.idle_add(dialog.finish)
                    self._finalize_conversion(
                        path,
                        tmp_output,
                        final_output,
                        "Image Converted (ffmpeg)",
                        f"{os.path.basename(path)} → {os.path.basename(final_output)}",
                        dialog,
                    )
                    return
                except subprocess.CalledProcessError:
                    pass

            self._notify(
                "Conversion failed", f"{os.path.basename(path)}: conversion tool error"
            )
        except Exception as e:
            self._notify("Conversion failed", f"{os.path.basename(path)}: {e}")

    def convert(self, menu, files, ext):
        magick_bin = self._find_magick()
        if not magick_bin:
            self._notify(
                "ImageMagick Not Found",
                "Please install ImageMagick to use this extension.",
            )
            return

        supported = self._discover_writable_formats(magick_bin)
        if ext not in supported:
            self._notify(
                "Format not supported", f"ImageMagick does not support .{ext} output."
            )
            return

        for fileinfo in files:
            path = fileinfo.get_location().get_path()
            if path:
                filename = os.path.basename(path)
                dialog = ProgressDialog(filename, ext)
            else:
                dialog = None

            t = threading.Thread(
                target=self._convert_file,
                args=(magick_bin, fileinfo, ext, dialog),
                daemon=True,
            )
            t.start()

    _COMPRESS_PRESETS = {
        "lossless": {
            "jpg": ["-quality", "100"],
            "png": ["-define", "png:compression-level=9"],
            "webp": ["-quality", "100"],
            "avif": ["-quality", "100"],
            "heic": ["-quality", "100"],
            "gif": None,
            "tif": ["-compress", "lzw"],
            "bmp": None,
            "ico": None,
            "jxl": None,
            "psd": None,
            "pdf": ["-compress", "zip"],
        },
        "high": {
            "jpg": ["-quality", "85"],
            "png": ["-colors", "256", "-define", "png:compression-level=9"],
            "webp": ["-quality", "85"],
            "avif": ["-quality", "80"],
            "heic": ["-quality", "85"],
            "gif": None,
            "tif": ["-compress", "lzw"],
            "bmp": None,
            "ico": None,
            "jxl": ["-quality", "90"],
            "psd": None,
            "pdf": ["-compress", "zip"],
        },
        "medium": {
            "jpg": ["-quality", "65"],
            "png": ["-colors", "128", "-define", "png:compression-level=9"],
            "webp": ["-quality", "65"],
            "avif": ["-quality", "55"],
            "heic": ["-quality", "65"],
            "gif": ["-colors", "128"],
            "tif": ["-compress", "jpeg", "-quality", "65"],
            "bmp": None,
            "ico": None,
            "jxl": ["-quality", "75"],
            "psd": None,
            "pdf": ["-compress", "jpeg", "-quality", "65"],
        },
        "low": {
            "jpg": ["-quality", "35"],
            "png": ["-colors", "64", "-define", "png:compression-level=9"],
            "webp": ["-quality", "40"],
            "avif": ["-quality", "30"],
            "heic": ["-quality", "40"],
            "gif": ["-colors", "64"],
            "tif": ["-compress", "jpeg", "-quality", "40"],
            "bmp": None,
            "ico": None,
            "jxl": ["-quality", "50"],
            "psd": None,
            "pdf": ["-compress", "jpeg", "-quality", "40"],
        },
    }

    def _compress_file(self, magick_bin, fileinfo, quality, dialog=None):
        path = fileinfo.get_location().get_path()
        if not path:
            return

        try:
            mime = fileinfo.get_mime_type()
        except Exception:
            mime = None
        if mime and not mime.startswith("image/"):
            return

        src_ext = os.path.splitext(path)[1].lower().lstrip(".")
        if src_ext == "jpeg":
            src_ext = "jpg"

        ext = src_ext
        dir_name = os.path.dirname(path)
        base_name = os.path.basename(path)
        name_no_ext = os.path.splitext(base_name)[0]
        final_output = os.path.join(dir_name, f"{name_no_ext}_compressed.{ext}")
        tmp_output = os.path.join(dir_name, f".{base_name}.compress")

        if not dialog:
            dialog = ProgressDialog(os.path.basename(path), f"{quality}")

        presets = self._COMPRESS_PRESETS.get(quality, {}).get(ext)
        cmd = [magick_bin, path, "-strip"]
        if presets:
            cmd.extend(presets)
        cmd.append(f"{ext}:{tmp_output}")

        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            process.wait()

            if process.returncode != 0 or not os.path.exists(tmp_output):
                raise subprocess.CalledProcessError(
                    process.returncode, cmd, output="Output file not created"
                )

            GLib.idle_add(dialog.finish)

            def on_choice(choice):
                try:
                    if choice == "replace":
                        os.replace(tmp_output, path)
                        self._notify(
                            "Image Compressed",
                            f"{os.path.basename(path)} ({quality})",
                        )
                    elif choice == "keep_both":
                        os.replace(tmp_output, final_output)
                        self._notify(
                            "Image Compressed",
                            f"{os.path.basename(path)} → {os.path.basename(final_output)} ({quality})",
                        )
                except Exception as e:
                    self._notify("Error", f"Could not finalize: {e}")

            dialog.callback = on_choice
            return
        except subprocess.CalledProcessError:
            if shutil.which("ffmpeg"):
                try:
                    ff_cmd = ["ffmpeg", "-y", "-i", path]
                    q = {"lossless": 1, "high": 2, "medium": 4, "low": 6}.get(quality, 4)
                    if ext in ("jpg", "jpeg"):
                        ff_cmd += ["-q:v", str(q)]
                    elif ext == "png":
                        ff_cmd += ["-compression_level", str(9 if quality == "lossless" else 6)]
                    ff_cmd += [f"{ext}:{tmp_output}"] if ext in ("jpg", "jpeg", "png") else [tmp_output]
                    subprocess.run(
                        ff_cmd, check=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    )
                    GLib.idle_add(dialog.finish)

                    def on_choice(choice):
                        try:
                            if choice == "replace":
                                os.replace(tmp_output, path)
                            elif choice == "keep_both":
                                os.replace(tmp_output, final_output)
                            self._notify(
                                "Image Compressed",
                                f"{os.path.basename(path)} ({quality})",
                            )
                        except Exception as e:
                            self._notify("Error", f"Could not finalize: {e}")

                    dialog.callback = on_choice
                    return
                except subprocess.CalledProcessError:
                    pass

            self._notify(
                "Compression failed",
                f"{os.path.basename(path)}: compression tool error",
            )
        except Exception as e:
            self._notify("Compression failed", f"{os.path.basename(path)}: {e}")

    def compress(self, menu, files, quality):
        magick_bin = self._find_magick()
        if not magick_bin:
            self._notify(
                "ImageMagick Not Found",
                "Please install ImageMagick to use this extension.",
            )
            return

        for fileinfo in files:
            filename = os.path.basename(
                fileinfo.get_location().get_path() or "image"
            )
            dialog = ProgressDialog(filename, quality)
            t = threading.Thread(
                target=self._compress_file,
                args=(magick_bin, fileinfo, quality, dialog),
                daemon=True,
            )
            t.start()

    _COMMON_FORMATS = [
        "png", "jpg", "webp", "avif", "heic", "gif", "tif",
        "bmp", "ico", "jxl", "psd", "pdf",
    ]

    _FALLBACK_TOOLS = {
        "avif": "avifenc",
        "webp": "cwebp",
        "heic": "heif-enc",
    }

    def _discover_writable_formats(self, magick_bin):
        try:
            p = subprocess.run(
                [magick_bin, "-list", "format"],
                check=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True,
            )
        except Exception:
            return []

        text = p.stdout.lower()
        supported = []
        for ext in self._COMMON_FORMATS:
            in_im = ext in text
            fallback = shutil.which(self._FALLBACK_TOOLS.get(ext, ""))
            if in_im or fallback:
                supported.append(ext)
        return supported

    _INPUT_EXTS = {
        "png", "jpg", "jpeg", "gif", "bmp", "webp", "avif", "heic", "heif",
        "tiff", "tif", "svg", "ico", "cur", "psd", "xcf", "tga", "jp2",
        "jxl", "exr", "hdr", "pcx", "pbm", "pgm", "ppm", "xbm", "xpm",
        "wbmp", "qoi", "dds", "ras", "sgi", "eps", "pdf", "ps",
        "pict", "pct", "fits", "mng", "dpx", "cin", "xwd",
        "pam", "pgx", "phm", "mtv", "otb", "uhdr", "wpg", "dcm",
    }

    def _is_image_file(self, fileinfo):
        try:
            mime = fileinfo.get_mime_type()
        except Exception:
            mime = None
        if mime and mime.startswith("image/"):
            return True
        try:
            path = fileinfo.get_location().get_path()
        except Exception:
            path = None
        if not path:
            return False
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        return ext in self._INPUT_EXTS

    def get_file_items(self, *args):
        files = None
        if len(args) == 1:
            files = args[0]
        elif len(args) >= 2:
            files = args[1]

        if not files:
            return []

        try:
            all_images = all(self._is_image_file(f) for f in files)
        except Exception:
            all_images = False

        if not all_images:
            return []

        magick_bin = self._find_magick()
        if not magick_bin:
            return []

        supported = self._discover_writable_formats(magick_bin)
        items = []

        if supported:
            convert_parent = Nautilus.MenuItem(
                name="ImageConverter::Main", label="Convert Image"
            )
            convert_menu = Nautilus.Menu()
            for ext in supported:
                item = Nautilus.MenuItem(
                    name=f"ImageConverter::{ext}", label=f"To {ext.upper()}"
                )
                item.connect("activate", self.convert, files, ext)
                convert_menu.append_item(item)
            convert_parent.set_submenu(convert_menu)
            items.append(convert_parent)

        compress_parent = Nautilus.MenuItem(
            name="ImageConverter::Compress", label="Compress Image"
        )
        compress_menu = Nautilus.Menu()
        _compress_labels = {
            "lossless": "Lossless",
            "high": "High Quality (85%)",
            "medium": "Medium Quality (65%)",
            "low": "Low Quality (35%)",
        }
        for q in ("lossless", "high", "medium", "low"):
            item = Nautilus.MenuItem(
                name=f"ImageConverter::Compress::{q}",
                label=_compress_labels[q],
            )
            item.connect("activate", self.compress, files, q)
            compress_menu.append_item(item)
        compress_parent.set_submenu(compress_menu)
        items.append(compress_parent)

        return items
