import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import os
import json
import threading
import psutil
import subprocess
from PIL import Image
import re
import time

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

VIDEO_MODELS = {
    "Lite Restore": "lite_restore",
    "Pro Detail": "pro_detail",
    "Ultra Native": "ultra_native"
}

IMAGE_MODEL = {
    "Image Enhance": "image_enhance"
}

CONFIG_FILE = "config.json"

class NotYUpscalerZAI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NotY Upscaler ZAI")
        self.geometry("1480x960")
        self.minsize(1280, 800)

        self.configure(fg_color="#0d1117")

# ─── Window + Taskbar icon ───────────────────────────────────────
        import sys
        import os

        def resource_path(relative_path):
            """ Get absolute path to resource, works for dev and for PyInstaller """
            try:
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")

            return os.path.join(base_path, relative_path)

        # Try to set icon
        try:
            ico_path = resource_path("logo.ico")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
            else:
                # fallback — try relative to script
                self.iconbitmap("logo.ico")
        except Exception as e:
            print("Could not set window icon:", e)

        self.accent = "#00d4ff"
        self.success = "#00ff9d"
        self.danger  = "#ff5555"
        self.gray    = "#444c56"
        self.live_enabled = False

        self.current_path = None
        self.is_video = False
        self.cap = None
        self.playing = False
        self.current_frame_bgr = None
        self.output_folder = None

        self.current_orig_preview = None
        self.current_enh_preview  = None

        self.current_model_dict = VIDEO_MODELS

        self.export_running = False
        self.export_cancel_requested = False
        self.export_process = None

        self.load_config()
        self.detect_specs()

        self.create_ui()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config = json.load(f)
            except:
                self.config = {"specs_read": False, "preferred_device": "Auto"}
        else:
            self.config = {"specs_read": False, "preferred_device": "Auto"}

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f)

    def detect_specs(self):
        self.ram_gb = psutil.virtual_memory().total / (1024**3)
        self.cores = psutil.cpu_count(logical=False) or 2
        try:
            self.has_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0
        except:
            self.has_cuda = False

        if self.ram_gb < 8 or self.cores <= 2:
            self.recommended = "CPU only"
        elif self.has_cuda:
            self.recommended = "GPU (if available)"
        else:
            self.recommended = "Auto"

    def create_ui(self):
        # Top bar
        top = ctk.CTkFrame(self, height=64, fg_color="#161b22", corner_radius=0)
        top.pack(fill="x")
        top.pack_propagate(False)

        ctk.CTkLabel(top, text="NotY Upscaler ZAI", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=self.accent).pack(side="left", padx=24, pady=12)

        self.specs_label = ctk.CTkLabel(top, text=f"RAM: {self.ram_gb:.1f} GB • Cores: {self.cores} • {'CUDA' if self.has_cuda else 'CPU'}",
                                        font=ctk.CTkFont(size=13), text_color="#8b949e")
        self.specs_label.pack(side="right", padx=24, pady=12)

        # Main content
        content = ctk.CTkFrame(self, fg_color="#0d1117")
        content.pack(fill="both", expand=True)

        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=0)

        # Left: Preview Area
        left = ctk.CTkFrame(content, fg_color="#161b22", corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)
        left.grid_columnconfigure(1, weight=1)

        orig_panel = ctk.CTkFrame(left, fg_color="transparent")
        orig_panel.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        ctk.CTkLabel(orig_panel, text="ORIGINAL", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#8b949e").pack(pady=(12,4))
        self.orig_label = ctk.CTkLabel(orig_panel, text="Select media", width=680, height=460,
                                       fg_color="#0d1117", corner_radius=10)
        self.orig_label.pack(pady=8, expand=True, fill="both")

        enh_panel = ctk.CTkFrame(left, fg_color="transparent")
        enh_panel.grid(row=0, column=1, sticky="nsew", padx=(8,0))
        ctk.CTkLabel(enh_panel, text="ENHANCED", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=self.accent).pack(pady=(12,4))
        self.enh_label = ctk.CTkLabel(enh_panel, text="Live preview disabled", width=680, height=460,
                                      fg_color="#0d1117", corner_radius=10)
        self.enh_label.pack(pady=8, expand=True, fill="both")

        ctrl = ctk.CTkFrame(left, fg_color="#161b22")
        ctrl.grid(row=1, column=0, columnspan=2, sticky="ew", pady=12, padx=12)

        self.play_btn = ctk.CTkButton(ctrl, text="▶  Play", width=110, height=42,
                                      font=ctk.CTkFont(size=14), command=lambda: self.toggle_play())
        self.play_btn.pack(side="left", padx=8)

        self.timeline = ctk.CTkSlider(ctrl, from_=0, to=100,
                                      command=lambda v: self.on_timeline_change(v),
                                      height=24, button_length=32, fg_color="#21262d", progress_color=self.accent)
        self.timeline.pack(side="left", fill="x", expand=True, padx=12)
        self.timeline.set(0)

        ctk.CTkButton(ctrl, text="Open in Player", width=140, height=42,
                      command=lambda: self.open_in_system_player()).pack(side="right", padx=8)

        self.info_label = ctk.CTkLabel(left, text="No file loaded", font=ctk.CTkFont(size=13),
                                       text_color="#8b949e")
        self.info_label.grid(row=2, column=0, columnspan=2, pady=8)

        # Bottom-left controls (LHS bottom)
        bottom_left = ctk.CTkFrame(left, fg_color="#161b22")
        bottom_left.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12,16), padx=12)

        self.export_btn = ctk.CTkButton(bottom_left, text="Export", height=48,
                                        fg_color="#1f6feb", hover_color="#388bfd",
                                        font=ctk.CTkFont(size=15, weight="bold"),
                                        command=self.start_export)
        self.export_btn.pack(side="left", padx=8, fill="x", expand=True)

        self.preview_toggle_btn = ctk.CTkButton(bottom_left, text="Live Preview: OFF",
                                                fg_color="#21262d", hover_color="#30363d",
                                                command=self.toggle_live_preview, height=48)
        self.preview_toggle_btn.pack(side="right", padx=8)

        # Right sidebar
        right = ctk.CTkScrollableFrame(content, width=380, fg_color="#161b22", corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(0,16), pady=16)

        ctk.CTkLabel(right, text="INPUT & OUTPUT", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=24, pady=(24,8))

        ctk.CTkButton(right, text="📂  Select Image / Video", height=52,
                      font=ctk.CTkFont(size=15, weight="bold"),
                      fg_color=self.accent, text_color="#000000",
                      command=self.select_file).pack(pady=8, padx=24, fill="x")

        self.file_name = ctk.CTkLabel(right, text="No file selected", text_color="#8b949e")
        self.file_name.pack(pady=8)

        ctk.CTkButton(right, text="📁  Choose Output Folder", height=48,
                      fg_color="#238636", hover_color="#2ea043",
                      command=self.choose_output_folder).pack(pady=8, padx=24, fill="x")

        self.output_status = ctk.CTkLabel(right, text="Output: same as input", text_color="#8b949e")
        self.output_status.pack(pady=8)

        # Export Progress Section
        ctk.CTkLabel(right, text="EXPORT PROGRESS", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=24, pady=(24,8))

        self.progress_bar = ctk.CTkProgressBar(right, width=320, height=20, mode="determinate",
                                               fg_color="#21262d", progress_color=self.success)
        self.progress_bar.pack(pady=12, padx=24)
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()

        self.progress_label = ctk.CTkLabel(right, text="0%", font=ctk.CTkFont(size=16, weight="bold"),
                                           text_color=self.success)
        self.progress_label.pack(pady=4)
        self.progress_label.pack_forget()

        self.cancel_btn = ctk.CTkButton(right, text="✖  Cancel Export", height=42,
                                        fg_color=self.danger, hover_color="#cc0000",
                                        command=self.cancel_export)
        self.cancel_btn.pack(pady=8, padx=24, fill="x")
        self.cancel_btn.pack_forget()

        # Settings section
        ctk.CTkLabel(right, text="SETTINGS", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=24, pady=(24,8))

        ctk.CTkLabel(right, text="Model", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=24, pady=(8,4))
        self.model_var = ctk.StringVar(value="Ultra Native")
        self.model_menu = ctk.CTkOptionMenu(right, values=list(self.current_model_dict.keys()),
                                            variable=self.model_var, command=lambda v: self.live_update(),
                                            fg_color="#21262d", button_color="#30363d")
        self.model_menu.pack(padx=24, pady=6, fill="x")

        ctk.CTkLabel(right, text="Target Resolution", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=24, pady=(16,4))
        self.target_var = ctk.StringVar(value="Fit 4K")
        ctk.CTkOptionMenu(right, values=["Fit 2K","Fit 3K","Fit 4K"],
                          variable=self.target_var, fg_color="#21262d", button_color="#30363d").pack(padx=24, pady=6, fill="x")

        adj = ctk.CTkFrame(right, fg_color="#0d1117", corner_radius=8)
        adj.pack(pady=20, padx=24, fill="x")
        ctk.CTkLabel(adj, text="Sharpen Strength", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=12)
        self.sharpen_s = ctk.CTkSlider(adj, from_=0.5, to=4.0, command=lambda v: self.live_update())
        self.sharpen_s.set(2.2)
        self.sharpen_s.pack(padx=20, pady=(0,16), fill="x")

        self.status = ctk.CTkLabel(right, text="", text_color=self.accent, font=ctk.CTkFont(size=13))
        self.status.pack(pady=16)

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("Media","*.jpg *.jpeg *.png *.webp *.mp4 *.mkv *.avi *.mov")])
        if not path: return
        self.current_path = path
        self.is_video = path.lower().endswith(('.mp4','.mkv','.avi','.mov'))
        self.file_name.configure(text=os.path.basename(path)[:38])

        if self.is_video:
            self.current_model_dict = VIDEO_MODELS
            default = "Ultra Native"
        else:
            self.current_model_dict = IMAGE_MODEL
            default = "Image Enhance"

        self.model_var.set(default)
        self.model_menu.configure(values=list(self.current_model_dict.keys()))

        if self.is_video:
            self.load_video()
        else:
            self.load_image()

    def load_image(self):
        frame = cv2.imread(self.current_path)
        if frame is None:
            messagebox.showerror("Error", "Cannot load image")
            return
        self.current_frame_bgr = frame
        self.show_frame(frame, self.orig_label)
        self.timeline.configure(from_=0, to=1)
        h, w = frame.shape[:2]
        target_w, target_h = self.calculate_size(w, h)
        self.info_label.configure(text=f"{w}×{h}  →  {target_w}×{target_h}")
        self.live_update()

    def load_video(self):
        if self.cap: self.cap.release()
        self.cap = cv2.VideoCapture(self.current_path)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Cannot open video")
            return
        total = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.timeline.configure(from_=0, to=max(total-1, 1))
        self.timeline.set(0)
        self.update_video_frame()
        self.after(200, self.live_update)

    def update_video_frame(self):
        if not self.cap or not self.cap.isOpened(): return
        pos = int(self.timeline.get())
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ret, frame = self.cap.read()
        if ret:
            self.current_frame_bgr = frame
            self.show_frame(frame, self.orig_label)
            if not self.playing and self.live_enabled:
                self.live_update()
        if self.playing:
            self.after(33, self.update_video_frame)

    def show_frame(self, bgr, label):
        if bgr is None: return
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        pil = pil.resize((680, 460), Image.LANCZOS)
        cimg = ctk.CTkImage(pil, size=(680, 460))
        label.configure(image=cimg, text="")
        if label == self.enh_label:
            self.current_enh_preview = cimg
        else:
            self.current_orig_preview = cimg

    def toggle_play(self):
        if not self.is_video: return
        self.playing = not self.playing
        self.play_btn.configure(text="❚❚ Pause" if self.playing else "▶ Play")
        if self.playing:
            self.update_video_frame()

    def on_timeline_change(self, val):
        if self.is_video:
            self.update_video_frame()

    def live_update(self, val=None):
        if not self.live_enabled or self.current_frame_bgr is None:
            return
        try:
            sharpen = self.sharpen_s.get()
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(sharpen*3), int(sharpen*3)))
            enhanced = cv2.filter2D(self.current_frame_bgr.copy(), -1, kernel)
            self.show_frame(enhanced, self.enh_label)
        except Exception as e:
            print("Live preview error:", str(e))

    def toggle_live_preview(self):
        self.live_enabled = not self.live_enabled
        txt = "ON" if self.live_enabled else "OFF"
        col = self.accent if self.live_enabled else "#21262d"
        self.preview_toggle_btn.configure(text=f"Live Preview: {txt}", fg_color=col)
        if self.live_enabled and self.current_frame_bgr is not None:
            self.live_update()
        elif not self.live_enabled:
            self.enh_label.configure(text="Live preview disabled", image=None)

    def start_export(self):
        if self.export_running:
            messagebox.showwarning("Already Exporting", "An export process is already running.\nPlease wait or cancel it first.")
            return

        if not self.current_path:
            messagebox.showwarning("No file", "Please select a file first")
            return

        self.export_running = True
        self.export_cancel_requested = False
        self.export_btn.configure(state="disabled", text="Exporting...", fg_color="#444c56")
        self.progress_bar.pack(pady=12, padx=24)
        self.progress_label.pack(pady=4)
        self.cancel_btn.pack(pady=8, padx=24, fill="x")
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        self.status.configure(text="Starting export...")

        threading.Thread(target=self.export_thread, daemon=True).start()

    def export_thread(self):
        out_path = self.get_output_path(self.current_path)

        try:
            if not self.is_video:
                img = cv2.imread(self.current_path)
                if img is None:
                    raise ValueError("Cannot read image")
                h, w = img.shape[:2]
                nw, nh = self.calculate_size(w, h)
                up = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
                sharpen = self.sharpen_s.get()
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(sharpen*3), int(sharpen*3)))
                enhanced = cv2.filter2D(up, -1, kernel)
                cv2.imwrite(out_path, enhanced)
                self.after(0, lambda: self._update_progress(100))
            else:
                video_bitrate = 15000
                audio_bitrate = 320

                try:
                    cmd_v = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=bit_rate", "-of", "default=noprint_wrappers=1:nokey=1", self.current_path]
                    vbr = subprocess.check_output(cmd_v, stderr=subprocess.STDOUT).decode().strip()
                    if vbr.isdigit():
                        video_bitrate = int(vbr) // 1000
                except:
                    pass

                try:
                    cmd_a = ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=bit_rate", "-of", "default=noprint_wrappers=1:nokey=1", self.current_path]
                    abr = subprocess.check_output(cmd_a, stderr=subprocess.STDOUT).decode().strip()
                    if abr.isdigit():
                        audio_bitrate = int(abr) // 1000
                except:
                    pass

                cap = cv2.VideoCapture(self.current_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()

                nw, nh = self.calculate_size(w, h)
                sharpen = self.sharpen_s.get()
                vf = f"scale={nw}:{nh}:flags=lanczos,unsharp=5:5:{sharpen*1.5}"

                cmd = [
                    "ffmpeg", "-i", self.current_path,
                    "-vf", vf,
                    "-c:v", "libx264", "-preset", "medium",
                    "-b:v", f"{video_bitrate}k",
                    "-maxrate", f"{int(video_bitrate * 1.5)}k",
                    "-bufsize", f"{int(video_bitrate * 2)}k",
                    "-c:a", "aac", "-b:a", f"{audio_bitrate}k",
                    "-map", "0",
                    "-y", out_path
                ]

                # Run FFmpeg hidden (no console window)
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

                self.export_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                       text=True, bufsize=1, startupinfo=startupinfo)

                while self.export_process.poll() is None:
                    if self.export_cancel_requested:
                        self.export_process.terminate()
                        try:
                            time.sleep(0.5)
                            if os.path.exists(out_path):
                                os.remove(out_path)
                        except:
                            pass
                        self.after(0, lambda: messagebox.showinfo("Cancelled", "Export cancelled by user."))
                        break

                    line = self.export_process.stderr.readline()
                    if "frame=" in line:
                        try:
                            frame = int(re.search(r'frame=\s*(\d+)', line).group(1))
                            percent = min(100, int((frame / total_frames) * 100))
                            self.after(0, lambda p=percent: self._update_progress(p))
                        except:
                            pass
                    time.sleep(0.2)

                if self.export_process.returncode != 0 and not self.export_cancel_requested:
                    raise RuntimeError(f"FFmpeg failed (code {self.export_process.returncode})")

                if not self.export_cancel_requested:
                    self.after(0, lambda: self._update_progress(100))
                    self.after(0, lambda: messagebox.showinfo("Success", f"Exported to:\n{out_path}"))

        except Exception as e:
            self.after(0, lambda msg=str(e): messagebox.showerror("Export Failed", msg))
        finally:
            self.after(0, self._finish_export_ui)

    def _update_progress(self, percent):
        if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
            self.progress_bar.set(percent / 100.0)
            self.progress_label.configure(text=f"{percent}%")

    def _finish_export_ui(self):
        self.export_running = False
        self.export_cancel_requested = False
        self.export_process = None
        self.export_btn.configure(state="normal", text="Export", fg_color="#1f6feb")
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()
        self.cancel_btn.pack_forget()
        self.status.configure(text="Export finished")

    def cancel_export(self):
        if not self.export_running or not self.export_process:
            return
        self.export_cancel_requested = True
        self.status.configure(text="Cancelling export...", text_color=self.danger)
        self.progress_label.configure(text="Cancelling...")

    def calculate_size(self, w, h):
        t = self.target_var.get()
        targets = {"Fit 2K": (2560,1440), "Fit 3K": (2880,1620), "Fit 4K": (3840,2160)}
        tw, th = targets.get(t, (3840,2160))
        scale = min(tw / w, th / h)
        return int(w * scale // 2 * 2), int(h * scale // 2 * 2)

    def open_in_system_player(self):
        if self.current_path and os.path.exists(self.current_path):
            if os.name == 'nt':
                os.startfile(self.current_path)
            else:
                subprocess.call(['xdg-open' if os.name == 'posix' else 'open', self.current_path])

    def choose_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_status.configure(text=f"Output: {os.path.basename(folder)}", text_color=self.accent)

    def get_output_path(self, input_path):
        base, ext = os.path.splitext(os.path.basename(input_path))
        filename = f"{base}_enhanced{ext}"
        if self.output_folder and os.path.isdir(self.output_folder):
            return os.path.join(self.output_folder, filename)
        return os.path.join(os.path.dirname(input_path), filename)

    def read_specs(self):
        txt = f"RAM {self.ram_gb:.1f} GB • {self.cores} cores • {'CUDA' if self.has_cuda else 'CPU'}"
        self.status.configure(text=txt)
        self.config["specs_read"] = True
        self.save_config()

if __name__ == "__main__":
    app = NotYUpscalerZAI()
    app.mainloop()