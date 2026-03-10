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
import sys
import shutil
import numpy as np

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# FFmpeg helpers
def get_ffmpeg_path():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print("Using system FFmpeg")
        return "ffmpeg"
    except:
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        bundled = os.path.join(base, "ffmpeg.exe")
        if os.path.isfile(bundled):
            print("Using bundled FFmpeg")
            return bundled
        raise FileNotFoundError("FFmpeg not found. Install it or place ffmpeg.exe next to script.")

def get_ffprobe_path():
    try:
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return "ffprobe"
    except:
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        probe = os.path.join(base, "ffprobe.exe")
        return probe if os.path.isfile(probe) else None

VIDEO_MODELS = {
    "Lite Restore": "lite_restore",
    "Pro Detail": "pro_detail",
    "Ultra Native": "ultra_native"
}

IMAGE_MODEL = {
    "Image Enhance": "image_enhance"
}

CONFIG_FILE = "config.json"

FORMAT_CODECS = {
    "mp4":  {"c_v": "libx264", "c_a": "aac",  "f": None,     "movflags": "+faststart", "audio_b": "192k"},
    "mov":  {"c_v": "libx264", "c_a": "aac",  "f": "mov",    "movflags": None,         "audio_b": "192k"},
    "m4v":  {"c_v": "libx264", "c_a": "aac",  "f": "ipod",   "movflags": "+faststart", "audio_b": "192k"},
    "avi":  {"c_v": "mpeg4",   "c_a": "mp2",  "f": "avi",    "movflags": None,         "audio_b": "192k"},
    "mxf":  {"c_v": "mpeg2video", "c_a": "pcm_s16le", "f": "mxf", "movflags": None,   "audio_b": None},
    "3gp":  {"c_v": "mpeg4",   "c_a": "aac",  "f": "3gp",    "movflags": None,         "audio_b": "128k"}
}

class NotYUpscalerZAI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NotY Upscaler ZAI")
        self.geometry("1480x960")
        self.minsize(1280, 800)

        self.configure(fg_color="#0d1117")

        if os.path.exists("logo.ico"):
            try:
                self.iconbitmap("logo.ico")
            except:
                pass

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
        self.video_duration_sec = 0

        self.current_orig_preview = None
        self.current_enh_preview  = None
        self.current_enh_image    = None

        self.current_model_dict = VIDEO_MODELS
        self.current_model = None

        self.export_running = False
        self.export_cancel_requested = False
        self.export_process = None

        self.load_config()
        self.detect_specs()

        self.create_ui()

        self.last_preview_time = 0

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

    def create_ui(self):
        top = ctk.CTkFrame(self, height=64, fg_color="#161b22", corner_radius=0)
        top.pack(fill="x")
        top.pack_propagate(False)

        ctk.CTkLabel(top, text="NotY Upscaler ZAI", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
                     text_color=self.accent).pack(side="left", padx=24, pady=12)

        self.specs_label = ctk.CTkLabel(top, text=f"RAM: {self.ram_gb:.1f} GB • Cores: {self.cores} • {'CUDA' if self.has_cuda else 'CPU'}",
                                        font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#a0a0a0")
        self.specs_label.pack(side="right", padx=24, pady=12)

        content = ctk.CTkFrame(self, fg_color="#0d1117")
        content.pack(fill="both", expand=True, padx=12, pady=12)

        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(content, fg_color="#161b22", corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,8))

        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)
        left.grid_columnconfigure(1, weight=1)

        orig_panel = ctk.CTkFrame(left, fg_color="transparent")
        orig_panel.grid(row=0, column=0, sticky="nsew", padx=(8,4), pady=8)
        ctk.CTkLabel(orig_panel, text="ORIGINAL", font=ctk.CTkFont(size=15, weight="bold"), text_color="gray").pack(pady=(8,4))
        self.orig_label = ctk.CTkLabel(orig_panel, text="Select media", width=680, height=460, fg_color="#11151c", corner_radius=0)
        self.orig_label.pack(expand=True, fill="both")

        enh_panel = ctk.CTkFrame(left, fg_color="transparent")
        enh_panel.grid(row=0, column=1, sticky="nsew", padx=(4,8), pady=8)
        ctk.CTkLabel(enh_panel, text="ENHANCED", font=ctk.CTkFont(size=15, weight="bold"), text_color=self.accent).pack(pady=(8,4))
        self.enh_label = ctk.CTkLabel(enh_panel, text="Live preview disabled", width=680, height=460, fg_color="#11151c", corner_radius=0)
        self.enh_label.pack(expand=True, fill="both")

        ctrl = ctk.CTkFrame(left, fg_color="#161b22")
        ctrl.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10, padx=12)

        self.play_btn = ctk.CTkButton(ctrl, text="▶ Play", width=110, height=40, font=ctk.CTkFont(size=14), command=self.toggle_play)
        self.play_btn.pack(side="left", padx=8)

        self.timeline = ctk.CTkSlider(ctrl, from_=0, to=100, command=self.on_timeline_change,
                                      height=20, button_length=30, fg_color="#2a2f38", progress_color=self.accent)
        self.timeline.pack(side="left", fill="x", expand=True, padx=12)
        self.timeline.set(0)

        ctk.CTkButton(ctrl, text="Open in Player", width=140, height=40, command=self.open_in_system_player).pack(side="right", padx=8)

        self.info_label = ctk.CTkLabel(left, text="No file loaded", font=ctk.CTkFont(size=13), text_color="gray")
        self.info_label.grid(row=2, column=0, columnspan=2, pady=8)

        bottom_left = ctk.CTkFrame(left, fg_color="#161b22")
        bottom_left.grid(row=3, column=0, columnspan=2, sticky="ew", pady=12, padx=12)

        self.export_btn = ctk.CTkButton(bottom_left, text="Export", height=48, fg_color="#1e88e5", hover_color="#1565c0",
                                        font=ctk.CTkFont(size=15, weight="bold"), command=self.start_export)
        self.export_btn.pack(side="left", padx=8, fill="x", expand=True)

        self.preview_toggle_btn = ctk.CTkButton(bottom_left, text="Live Preview: OFF", height=48,
                                                fg_color="#2a2f38", hover_color="#3a3f48", command=self.toggle_live_preview)
        self.preview_toggle_btn.pack(side="right", padx=8)

        right = ctk.CTkScrollableFrame(content, width=380, fg_color="#161b22", corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(8,0), pady=0)

        ctk.CTkLabel(right, text="FILE & OUTPUT", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=24, pady=(20,8))

        self.select_btn = ctk.CTkButton(right, text="Select Image / Video", height=50,
                                        fg_color=self.accent, text_color="black", command=self.select_file)
        self.select_btn.pack(pady=6, padx=24, fill="x")

        self.file_name = ctk.CTkLabel(right, text="No file selected", text_color="gray")
        self.file_name.pack(pady=4)

        self.output_btn = ctk.CTkButton(right, text="Choose Output Folder", height=44,
                                        fg_color="#2e7d32", hover_color="#1b5e20", command=self.choose_output_folder)
        self.output_btn.pack(pady=6, padx=24, fill="x")

        self.output_status = ctk.CTkLabel(right, text="Output: same as input", text_color="gray")
        self.output_status.pack(pady=4)

        ctk.CTkLabel(right, text="EXPORT PROGRESS", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=24, pady=(24,8))

        self.progress_bar = ctk.CTkProgressBar(right, width=320, height=18, mode="determinate",
                                               fg_color="#2a2f38", progress_color=self.success)
        self.progress_bar.pack(pady=8, padx=24)
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()

        self.progress_label = ctk.CTkLabel(right, text="0%", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.success)
        self.progress_label.pack(pady=4)
        self.progress_label.pack_forget()

        self.cancel_btn = ctk.CTkButton(right, text="Cancel Export", height=44,
                                        fg_color=self.danger, hover_color="#c62828", command=self.cancel_export)
        self.cancel_btn.pack(pady=8, padx=24, fill="x")
        self.cancel_btn.pack_forget()

        ctk.CTkLabel(right, text="SETTINGS", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=24, pady=(24,8))

        ctk.CTkLabel(right, text="Model", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=24, pady=(8,2))
        self.model_var = ctk.StringVar(value="Ultra Native")
        self.model_menu = ctk.CTkOptionMenu(right, values=list(self.current_model_dict.keys()),
                                            variable=self.model_var,
                                            command=self.on_model_change,
                                            fg_color="#2a2f38", button_color="#3a3f48")
        self.model_menu.pack(padx=24, pady=4, fill="x")

        ctk.CTkLabel(right, text="Target Resolution", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=24, pady=(12,2))
        self.target_var = ctk.StringVar(value="Fit 4K")
        self.target_menu = ctk.CTkOptionMenu(right, values=["Fit 2K","Fit 3K","Fit 4K"],
                                             variable=self.target_var, fg_color="#2a2f38", button_color="#3a3f48")
        self.target_menu.pack(padx=24, pady=4, fill="x")

        self.format_frame = ctk.CTkFrame(right, fg_color="transparent")
        ctk.CTkLabel(self.format_frame, text="Output Format", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=24, pady=(12,2))
        self.format_var = ctk.StringVar(value="mp4")
        self.format_menu = ctk.CTkOptionMenu(self.format_frame, values=list(FORMAT_CODECS.keys()),
                                             variable=self.format_var, fg_color="#2a2f38", button_color="#3a3f48")
        self.format_menu.pack(padx=24, pady=4, fill="x")

        adj = ctk.CTkFrame(right, fg_color="#1e1e2e", corner_radius=8)
        adj.pack(pady=16, padx=20, fill="x")

        bitrate_frame = ctk.CTkFrame(adj, fg_color="transparent")
        bitrate_frame.pack(fill="x", pady=8)

        ctk.CTkLabel(bitrate_frame, text="Bitrate (Mbps) - Video only", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=4)
        self.bitrate_s = ctk.CTkSlider(bitrate_frame, from_=4, to=60, number_of_steps=56, command=self.on_bitrate_change,
                                       fg_color="#2a2f38", progress_color=self.success)
        self.bitrate_s.set(12)
        self.bitrate_s.pack(padx=4, pady=(4,0), fill="x")

        self.bitrate_label = ctk.CTkLabel(bitrate_frame, text="12 Mbps", font=ctk.CTkFont(size=13))
        self.bitrate_label.pack(anchor="w", padx=4, pady=2)

        self.size_estimate_label = ctk.CTkLabel(adj, text="Estimated size: —", font=ctk.CTkFont(size=13), text_color="#a0a0ff")
        self.size_estimate_label.pack(pady=12, anchor="w", padx=20)

        self.status = ctk.CTkLabel(right, text="", text_color=self.accent, font=ctk.CTkFont(size=13))
        self.status.pack(pady=16)

        self.format_frame.pack_forget()

    def on_bitrate_change(self, value):
        self.bitrate_label.configure(text=f"{int(value)} Mbps")
        self.update_size_estimate()

    def update_size_estimate(self):
        if not self.is_video or not self.video_duration_sec:
            self.size_estimate_label.configure(text="Estimated size: —")
            return

        bitrate_mbps = self.bitrate_s.get()
        size_mb = (bitrate_mbps * self.video_duration_sec * 1.15) / 8
        if size_mb > 1024:
            text = f"~{size_mb/1024:.1f} GB"
            color = "#ff9800" if size_mb > 5000 else "#a0a0ff"
        else:
            text = f"~{size_mb:.1f} MB"
            color = "#a0a0ff"

        self.size_estimate_label.configure(text=f"Estimated size: {text}", text_color=color)

    def on_model_change(self, selected):
        self.model_var.set(selected)
        self.update_model()
        if self.live_enabled and self.current_frame_bgr is not None:
            self.live_update()

    def update_model(self):
        model_name = self.model_var.get()
        try:
            if self.is_video:
                if model_name == "Lite Restore":
                    from models.lite_restore import LiteRestoreEnhancer
                    self.current_model = LiteRestoreEnhancer()
                elif model_name == "Pro Detail":
                    from models.pro_detail import ProDetailEnhancer
                    self.current_model = ProDetailEnhancer()
                else:
                    from models.ultra_native import UltraNativeEnhancer
                    self.current_model = UltraNativeEnhancer()
            else:
                from models.image_enhance import ImageEnhanceModel
                self.current_model = ImageEnhanceModel()
        except Exception as e:
            messagebox.showerror("Model Error", f"Failed to load model:\n{str(e)}")
            self.current_model = None

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("Media","*.jpg *.jpeg *.png *.webp *.mp4 *.mkv *.avi *.mov")])
        if not path:
            return

        self.current_path = path
        self.is_video = path.lower().endswith(('.mp4','.mkv','.avi','.mov'))
        self.file_name.configure(text=os.path.basename(path)[:40])

        if self.is_video:
            self.format_frame.pack(fill="x", pady=(8,0))
            self.update_size_estimate()
        else:
            self.format_frame.pack_forget()
            self.size_estimate_label.configure(text="Estimated size: —")

        if self.is_video:
            self.current_model_dict = VIDEO_MODELS
            default = "Ultra Native"
        else:
            self.current_model_dict = IMAGE_MODEL
            default = "Image Enhance"

        self.model_var.set(default)
        self.model_menu.configure(values=list(self.current_model_dict.keys()))
        self.update_model()

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
        if self.live_enabled:
            self.live_update()

    def load_video(self):
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.current_path)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Cannot open video")
            return

        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.video_duration_sec = total_frames / fps if fps > 0 else 0

        self.timeline.configure(from_=0, to=max(total_frames-1, 1))
        self.timeline.set(0)
        self.update_video_frame()
        self.update_size_estimate()

        if self.live_enabled:
            self.after(200, self.live_update)

    def update_video_frame(self):
        if not self.cap or not self.cap.isOpened():
            return
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
        if bgr is None:
            return
        try:
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(rgb)
            w, h = pil.size
            max_w, max_h = 680, 460
            ratio = min(max_w / w, max_h / h)
            new_size = (int(w * ratio), int(h * ratio))
            resized = pil.resize(new_size, Image.LANCZOS)
            bg = Image.new('RGB', (max_w, max_h), (13, 17, 23))
            bg.paste(resized, ((max_w - new_size[0]) // 2, (max_h - new_size[1]) // 2))
            cimg = ctk.CTkImage(bg, size=(680, 460))

            if label == self.enh_label:
                self.current_enh_image = cimg
                self.current_enh_preview = cimg
            else:
                self.current_orig_preview = cimg

            label.configure(image=cimg, text="")
        except Exception as e:
            print("show_frame error:", str(e))

    def toggle_play(self):
        if not self.is_video:
            return
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

        current_time = time.time()
        if current_time - self.last_preview_time < 0.15:
            return
        self.last_preview_time = current_time

        try:
            frame = self.current_frame_bgr.copy()
            # Pure natural enhancement for live preview (same as export)
            frame = cv2.bilateralFilter(frame, d=9, sigmaColor=75, sigmaSpace=75)
            frame = cv2.convertScaleAbs(frame, alpha=1.08, beta=5)  # mild contrast
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Laplacian(gray, cv2.CV_64F)
            edges = cv2.convertScaleAbs(edges)
            edges = cv2.GaussianBlur(edges, (0,0), 1.0)
            frame = cv2.addWeighted(frame, 1.0, cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR), 0.25, 0)
            self.show_frame(frame, self.enh_label)
        except Exception as e:
            print("Live preview error:", str(e))

    def toggle_live_preview(self):
        self.live_enabled = not self.live_enabled
        txt = "ON" if self.live_enabled else "OFF"
        col = self.accent if self.live_enabled else "#2a2f38"
        self.preview_toggle_btn.configure(text=f"Live Preview: {txt}", fg_color=col)

        if self.live_enabled and self.current_frame_bgr is not None:
            self.live_update()
        else:
            try:
                self.enh_label.configure(text="Live preview disabled", image="")
                self.current_enh_image = None
            except Exception:
                pass

    def start_export(self):
        if self.export_running:
            messagebox.showwarning("Busy", "Export already running.")
            return
        if not self.current_path:
            messagebox.showwarning("No file", "Select a file first.")
            return
        if self.current_model is None:
            messagebox.showwarning("Model error", "Model failed to load.")
            return

        self.disable_ui()
        self.export_running = True
        self.export_cancel_requested = False
        self.export_btn.configure(state="disabled", text="Exporting...", fg_color="#444c56")
        self.progress_bar.pack(pady=12, padx=24)
        self.progress_bar.set(0)
        self.progress_label.pack(pady=4)
        self.progress_label.configure(text="0%")
        self.cancel_btn.pack(pady=8, padx=24, fill="x")
        self.status.configure(text="Starting export...")

        threading.Thread(target=self.export_thread, daemon=True).start()

    def disable_ui(self):
        widgets = [
            self.select_btn, self.output_btn, self.model_menu, self.target_menu,
            self.format_menu, self.bitrate_s,
            self.play_btn, self.timeline, self.preview_toggle_btn, self.export_btn
        ]
        for w in widgets:
            if w and w.winfo_exists():
                w.configure(state="disabled")

    def enable_ui(self):
        widgets = [
            self.select_btn, self.output_btn, self.model_menu, self.target_menu,
            self.format_menu, self.bitrate_s,
            self.play_btn, self.timeline, self.preview_toggle_btn, self.export_btn
        ]
        for w in widgets:
            if w and w.winfo_exists():
                w.configure(state="normal")

    def export_thread(self):
        out_path = self.get_output_path(self.current_path)
        error_msg = None

        try:
            ffmpeg_path = get_ffmpeg_path()

            if not self.is_video:
                # Pure natural image enhancement (no sharpen slider)
                img = cv2.imread(self.current_path)
                if img is None:
                    raise ValueError("Cannot read image")
                h, w = img.shape[:2]
                nw, nh = self.calculate_size(w, h)
                up = cv2.resize(img, (nw, nh), cv2.INTER_LANCZOS4)

                # Natural enhancement steps
                up = cv2.bilateralFilter(up, d=9, sigmaColor=75, sigmaSpace=75)  # noise reduction
                up = cv2.convertScaleAbs(up, alpha=1.12, beta=8)  # gentle contrast & brightness
                gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
                edges = cv2.Laplacian(gray, cv2.CV_64F)
                edges = cv2.convertScaleAbs(edges)
                edges = cv2.GaussianBlur(edges, (0,0), 1.2)
                up = cv2.addWeighted(up, 1.0, cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR), 0.28, 0)

                cv2.imwrite(out_path, up, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
                self.after(0, lambda: self._update_progress(100))
            else:
                probe = get_ffprobe_path()
                audio_bitrate = "192k"
                if probe:
                    try:
                        cmd = [probe, "-v", "error", "-select_streams", "a:0",
                               "-show_entries", "stream=bit_rate", "-of", "default=noprint_wrappers=1:nokey=1",
                               self.current_path]
                        abr = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
                        if abr.isdigit():
                            audio_bitrate = f"{int(abr)//1000}k"
                    except:
                        pass

                cap = cv2.VideoCapture(self.current_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()

                nw, nh = self.calculate_size(w, h)

                # Auto preset based on bitrate
                bitrate_mbps = self.bitrate_s.get()
                if bitrate_mbps <= 8:
                    preset = "veryfast"
                elif bitrate_mbps <= 15:
                    preset = "faster"
                elif bitrate_mbps <= 25:
                    preset = "fast"
                elif bitrate_mbps <= 40:
                    preset = "medium"
                else:
                    preset = "slow"

                vf = f"scale={nw}:{nh}:flags=lanczos"

                video_bitrate = f"{int(bitrate_mbps * 1000)}k"
                maxrate      = f"{int(bitrate_mbps * 1.5 * 1000)}k"
                bufsize      = f"{int(bitrate_mbps * 2 * 1000)}k"

                fmt = self.format_var.get()
                fc = FORMAT_CODECS.get(fmt, FORMAT_CODECS["mp4"])
                audio_b = fc.get("audio_b", audio_bitrate)

                cmd = [
                    ffmpeg_path, "-i", self.current_path,
                    "-vf", vf,
                    "-c:v", fc["c_v"],
                    "-preset", preset,
                    "-b:v", video_bitrate,
                    "-maxrate", maxrate,
                    "-bufsize", bufsize,
                    "-c:a", fc["c_a"],
                    "-b:a", audio_b,
                    "-pix_fmt", "yuv420p",
                    "-map", "0",
                ]

                if fc.get("f"):
                    cmd += ["-f", fc["f"]]
                if fc.get("movflags"):
                    cmd += ["-movflags", fc["movflags"]]

                cmd += ["-y", out_path]

                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE

                self.export_process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, bufsize=1, startupinfo=startupinfo, universal_newlines=True
                )

                last_frame = 0
                while self.export_process.poll() is None:
                    if self.export_cancel_requested:
                        self.export_process.terminate()
                        self.export_process.wait(timeout=6)
                        if os.path.exists(out_path):
                            try:
                                os.remove(out_path)
                            except:
                                pass
                        self.after(0, lambda: messagebox.showinfo("Cancelled", "Export cancelled."))
                        break

                    for _ in range(20):
                        line = self.export_process.stderr.readline()
                        if not line:
                            break
                        if "frame=" in line:
                            try:
                                m = re.search(r'frame=\s*(\d+)', line)
                                if m:
                                    frame = int(m.group(1))
                                    if frame > last_frame:
                                        last_frame = frame
                                        percent = min(100, int((frame / total_frames) * 100))
                                        self.after(0, lambda p=percent: self._update_progress(p))
                            except:
                                pass

                    time.sleep(0.07)

                if self.export_process.returncode != 0 and not self.export_cancel_requested:
                    err = self.export_process.stderr.read(2048)
                    error_msg = f"FFmpeg failed (code {self.export_process.returncode})\n{err}"
                    raise RuntimeError(error_msg)

                if not self.export_cancel_requested:
                    self.after(0, lambda: self._update_progress(100))
                    self.after(0, lambda: messagebox.showinfo("Success", f"Saved to:\n{out_path}"))

        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda msg=error_msg: messagebox.showerror("Export Failed", msg))
        finally:
            self.after(0, self._finish_export_ui)

    def _update_progress(self, percent):
        if self.progress_bar and self.progress_bar.winfo_exists():
            self.progress_bar.set(percent / 100.0)
            self.progress_label.configure(text=f"{percent}%")

    def _finish_export_ui(self):
        self.export_running = False
        self.export_cancel_requested = False
        self.export_process = None
        self.export_btn.configure(state="normal", text="Export", fg_color="#1e88e5")
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()
        self.cancel_btn.pack_forget()
        self.status.configure(text="Export finished" if not self.export_cancel_requested else "Cancelled")
        self.enable_ui()

    def cancel_export(self):
        if not self.export_running or not self.export_process:
            return
        self.export_cancel_requested = True
        self.status.configure(text="Cancelling...", text_color=self.danger)
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
        base, _ = os.path.splitext(os.path.basename(input_path))
        if self.is_video:
            ext = f".{self.format_var.get()}"
        else:
            ext = os.path.splitext(input_path)[1]
        filename = f"{base}_enhanced{ext}"
        if self.output_folder and os.path.isdir(self.output_folder):
            return os.path.join(self.output_folder, filename)
        return os.path.join(os.path.dirname(input_path), filename)

if __name__ == "__main__":
    app = NotYUpscalerZAI()
    app.mainloop()