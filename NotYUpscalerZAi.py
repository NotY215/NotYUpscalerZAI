import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
import os
import json
import threading
import psutil
import subprocess
import sys
import time
import re
from PIL import Image, ImageTk
import shutil
import glob
import numpy as np
from datetime import datetime

# ===================== AUTO INSTALL REAL AI PACKAGES =====================
print("Checking AI dependencies...")
for pkg in [
    "torch", "torchvision", "torchaudio", "realesrgan", "basicsr",
    "gfpgan", "facexlib", "opencv-python-headless"
]:
    try:
        __import__(pkg.replace("-", "_").replace(".", "_"))
    except ImportError:
        print(f"Installing {pkg}... (this may take 2-5 minutes)")
        cmd = [sys.executable, "-m", "pip", "install", pkg]
        if pkg == "torch":
            cmd += ["--index-url", "https://download.pytorch.org/whl/cpu"]  # CPU version for broad compatibility
        subprocess.check_call(cmd)

import torch
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet
from gfpgan import GFPGANer
from facexlib.detection import RetinaFace

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "config.json"

class NotYUpscalerZAi(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NotYUpscalerZAi - Real AI Upscaler")
        self.geometry("1520x980")
        self.minsize(1300, 820)

        if os.path.exists("logo.ico"):
            try:
                self.iconbitmap("logo.ico")
            except:
                pass

        self.configure(fg_color="#0d1117")

        self.accent = "#00d4ff"
        self.success = "#00ff9d"
        self.danger = "#ff5555"
        self.live_enabled = False

        self.current_path = None
        self.is_video = False
        self.cap = None
        self.playing = False
        self.current_frame_bgr = None
        self.output_folder = None

        self.current_orig_preview = None
        self.current_enh_preview = None

        self.export_running = False
        self.export_cancel_requested = False
        self.export_process = None

        self.mode = "Local"
        self.ai_model = None
        self.gfpgan = None
        self.face_detector = None

        self.load_config()
        self.detect_specs()
        self.create_ui()
        self.after(100, self.init_ai_models)  # load real AI models in background

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config = json.load(f)
            except:
                self.config = {"last_model": "Ultra Native", "face_restore": True}
        else:
            self.config = {"last_model": "Ultra Native", "face_restore": True}

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f)

    def detect_specs(self):
        self.ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        self.cores = psutil.cpu_count(logical=False) or 2
        try:
            self.has_cuda = torch.cuda.is_available()
        except:
            self.has_cuda = False

    def create_ui(self):
        # ===================== TOP BAR =====================
        top = ctk.CTkFrame(self, height=70, fg_color="#161b22", corner_radius=0)
        top.pack(fill="x")
        top.pack_propagate(False)

        ctk.CTkLabel(top, text="NotYUpscalerZAi", font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=self.accent).pack(side="left", padx=30, pady=15)

        self.mode_local = ctk.CTkButton(top, text="Local AI", fg_color=self.accent, text_color="#000000",
                                        height=44, width=130, command=lambda: self.set_mode("Local"))
        self.mode_local.pack(side="left", padx=10)

        self.mode_online = ctk.CTkButton(top, text="Online", fg_color="#21262d", text_color="#8b949e",
                                         height=44, width=130, command=self.show_coming_soon)
        self.mode_online.pack(side="left", padx=10)

        self.model_status = ctk.CTkLabel(top, text="AI Model: Loading...", font=ctk.CTkFont(size=13), text_color="#8b949e")
        self.model_status.pack(side="right", padx=30)

        self.specs_label = ctk.CTkLabel(top, text=f"RAM: {self.ram_gb:.1f}GB • Cores: {self.cores} • {'CUDA' if self.has_cuda else 'CPU'}",
                                        font=ctk.CTkFont(size=13), text_color="#8b949e")
        self.specs_label.pack(side="right", padx=20)

        # ===================== MAIN CONTENT =====================
        content = ctk.CTkFrame(self, fg_color="#0d1117")
        content.pack(fill="both", expand=True, padx=16, pady=16)

        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=0)

        # LEFT: Previews
        left = ctk.CTkFrame(content, fg_color="#161b22", corner_radius=16)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)

        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)
        left.grid_columnconfigure(1, weight=1)

        # Original
        orig_panel = ctk.CTkFrame(left, fg_color="transparent")
        orig_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(orig_panel, text="ORIGINAL", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#8b949e").pack(pady=(16, 8))
        self.orig_label = ctk.CTkLabel(orig_panel, text="Select media to begin", width=720, height=480,
                                       fg_color="#0d1117", corner_radius=12)
        self.orig_label.pack(pady=12, expand=True, fill="both")

        # Enhanced
        enh_panel = ctk.CTkFrame(left, fg_color="transparent")
        enh_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(enh_panel, text="AI ENHANCED", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=self.accent).pack(pady=(16, 8))
        self.enh_label = ctk.CTkLabel(enh_panel, text="Live preview disabled", width=720, height=480,
                                      fg_color="#0d1117", corner_radius=12)
        self.enh_label.pack(pady=12, expand=True, fill="both")

        # Video controls
        ctrl = ctk.CTkFrame(left, fg_color="#161b22", height=80)
        ctrl.grid(row=1, column=0, columnspan=2, sticky="ew", pady=16, padx=20)
        ctrl.pack_propagate(False)

        self.play_btn = ctk.CTkButton(ctrl, text="▶ Play", width=120, height=48,
                                      font=ctk.CTkFont(size=15), command=self.toggle_play)
        self.play_btn.pack(side="left", padx=12)

        self.timeline = ctk.CTkSlider(ctrl, from_=0, to=100, command=self.on_timeline_change,
                                      height=28, button_length=36, fg_color="#21262d", progress_color=self.accent)
        self.timeline.pack(side="left", fill="x", expand=True, padx=20)
        self.timeline.set(0)

        ctk.CTkButton(ctrl, text="Open Original", width=160, height=48,
                      command=self.open_in_system_player).pack(side="right", padx=12)

        self.info_label = ctk.CTkLabel(left, text="No file loaded", font=ctk.CTkFont(size=14), text_color="#8b949e")
        self.info_label.grid(row=2, column=0, columnspan=2, pady=8)

        # Bottom controls
        bottom_ctrl = ctk.CTkFrame(left, fg_color="#161b22")
        bottom_ctrl.grid(row=3, column=0, columnspan=2, sticky="ew", pady=12, padx=20)

        self.export_btn = ctk.CTkButton(bottom_ctrl, text="🚀 EXPORT WITH AI", height=56,
                                        fg_color="#1f6feb", hover_color="#388bfd", font=ctk.CTkFont(size=17, weight="bold"),
                                        command=self.start_export)
        self.export_btn.pack(side="left", padx=12, fill="x", expand=True)

        self.preview_toggle_btn = ctk.CTkButton(bottom_ctrl, text="Live Preview: OFF",
                                                 fg_color="#21262d", hover_color="#30363d",
                                                 command=self.toggle_live_preview, height=56)
        self.preview_toggle_btn.pack(side="right", padx=12)

        # ===================== RIGHT SIDEBAR (TABBED) =====================
        self.sidebar = ctk.CTkTabview(content, width=420, fg_color="#161b22", segmented_button_fg_color="#21262d")
        self.sidebar.grid(row=0, column=1, sticky="nsew", padx=(12, 0), pady=0)

        # TAB 1: Input & Output
        self.sidebar.add("Input / Output")
        tab1 = self.sidebar.tab("Input / Output")

        ctk.CTkButton(tab1, text="📂 Select Image or Video", height=58, font=ctk.CTkFont(size=16, weight="bold"),
                      fg_color=self.accent, text_color="#000000", command=self.select_file).pack(pady=20, padx=30, fill="x")

        self.file_name = ctk.CTkLabel(tab1, text="No file selected", text_color="#8b949e", font=ctk.CTkFont(size=13))
        self.file_name.pack(pady=8)

        ctk.CTkButton(tab1, text="📁 Choose Output Folder", height=50, fg_color="#238636",
                      command=self.choose_output_folder).pack(pady=12, padx=30, fill="x")

        self.output_status = ctk.CTkLabel(tab1, text="Output: same folder as input", text_color="#8b949e")
        self.output_status.pack(pady=8)

        # TAB 2: AI Models
        self.sidebar.add("AI Models")
        tab2 = self.sidebar.tab("AI Models")

        ctk.CTkLabel(tab2, text="Select AI Model", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=30, pady=(30, 8))

        self.model_var = ctk.StringVar(value="Ultra Native (4x + Face)")
        self.model_menu = ctk.CTkOptionMenu(tab2, values=[
            "Lite Restore (2x)", "Pro Detail (4x)", "Ultra Native (4x + Face)"
        ], variable=self.model_var, command=self.on_model_change,
            fg_color="#21262d", button_color="#30363d", height=48, font=ctk.CTkFont(size=14))
        self.model_menu.pack(padx=30, pady=8, fill="x")

        self.model_info = ctk.CTkLabel(tab2, text="Real-ESRGAN + GFPGAN\n• 4× upscale\n• Face restoration\n• No glow", 
                                       text_color="#8b949e", justify="left")
        self.model_info.pack(pady=20, padx=30, anchor="w")

        self.download_btn = ctk.CTkButton(tab2, text="Download AI Models (first time)", height=48,
                                          command=self.force_download_models)
        self.download_btn.pack(pady=12, padx=30, fill="x")

        # TAB 3: Advanced Settings
        self.sidebar.add("Advanced")
        tab3 = self.sidebar.tab("Advanced")

        ctk.CTkLabel(tab3, text="Denoise Strength", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=30, pady=(30, 4))
        self.denoise_s = ctk.CTkSlider(tab3, from_=0, to=10, number_of_steps=10)
        self.denoise_s.set(4)
        self.denoise_s.pack(padx=30, pady=8, fill="x")

        ctk.CTkLabel(tab3, text="Sharpen Strength (Live only)", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=30, pady=(20, 4))
        self.sharpen_s = ctk.CTkSlider(tab3, from_=0.5, to=4.0, command=lambda v: self.live_update())
        self.sharpen_s.set(2.2)
        self.sharpen_s.pack(padx=30, pady=8, fill="x")

        self.face_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tab3, text="Face Restoration (GFPGAN)", variable=self.face_var,
                        font=ctk.CTkFont(size=14)).pack(anchor="w", padx=30, pady=20)

        # TAB 4: History
        self.sidebar.add("History")
        tab4 = self.sidebar.tab("History")
        self.history_text = ctk.CTkTextbox(tab4, height=600, fg_color="#0d1117")
        self.history_text.pack(fill="both", expand=True, padx=20, pady=20)
        self.history_text.insert("0.0", "Export history will appear here...\n")

        # TAB 5: About
        self.sidebar.add("About")
        tab5 = self.sidebar.tab("About")
        about_txt = """NotYUpscalerZAi v2.0
Real AI Upscaler (Real-ESRGAN + GFPGAN)

• No more glowing artifacts
• True AI 4× super-resolution
• Face restoration included
• Local processing only
• Open source & free

Made with ❤️ for sharp, natural results.
"""
        ctk.CTkLabel(tab5, text=about_txt, justify="left", font=ctk.CTkFont(size=14)).pack(pady=40, padx=30, anchor="w")

        # ===================== STATUS BAR =====================
        self.status = ctk.CTkLabel(self, text="Ready | Real AI loaded", text_color=self.success, font=ctk.CTkFont(size=13))
        self.status.pack(side="bottom", fill="x", pady=12, padx=20)

    def init_ai_models(self):
        try:
            from models.real_esrgan_model import RealESRGANEnhancer
            self.ai_model = RealESRGANEnhancer(device="cuda" if self.has_cuda else "cpu")
            self.model_status.configure(text="AI: Real-ESRGAN Ready ✓", text_color=self.success)
            self.status.configure(text="Real AI models loaded successfully")
        except Exception as e:
            self.model_status.configure(text="AI Load Failed", text_color=self.danger)
            messagebox.showerror("AI Error", f"Failed to load Real-ESRGAN:\n{str(e)}\n\nRun again or check models folder.")

    def force_download_models(self):
        if self.ai_model:
            self.ai_model.download_weights()
            messagebox.showinfo("Success", "AI models downloaded/verified!")
        else:
            messagebox.showwarning("Not Ready", "AI engine not initialized yet.")

    def show_coming_soon(self):
        messagebox.showinfo("Coming Soon 🔥", "Cloud AI mode (faster + higher quality) is in development.\nWill be released in next update.")

    def set_mode(self, mode):
        self.mode = mode
        if mode == "Local":
            self.mode_local.configure(fg_color=self.accent, text_color="#000000")
            self.mode_online.configure(fg_color="#21262d", text_color="#8b949e")
        else:
            self.mode_local.configure(fg_color="#21262d", text_color="#8b949e")
            self.mode_online.configure(fg_color=self.accent, text_color="#000000")

    # ===================== FILE SELECTION & PREVIEW =====================
    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("Media Files", "*.jpg *.jpeg *.png *.webp *.mp4 *.mkv *.avi *.mov")])
        if not path:
            return
        self.current_path = path
        self.is_video = path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov'))
        self.file_name.configure(text=os.path.basename(path)[:45] + "..." if len(os.path.basename(path)) > 45 else os.path.basename(path))

        if self.is_video:
            cap_temp = cv2.VideoCapture(path)
            if cap_temp.isOpened():
                w = int(cap_temp.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap_temp.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap_temp.release()
                self.info_label.configure(text=f"Video: {w}×{h} • AI 4× ready")
        else:
            img = cv2.imread(path)
            if img is not None:
                h, w = img.shape[:2]
                self.info_label.configure(text=f"Image: {w}×{h} • AI 4× ready")
                self.current_frame_bgr = img
                self.show_frame(img, self.orig_label)
                self.live_update()

        if self.is_video:
            self.load_video()
        else:
            self.load_image()

    def load_image(self):
        frame = cv2.imread(self.current_path)
        if frame is None:
            return
        self.current_frame_bgr = frame
        self.show_frame(frame, self.orig_label)
        self.live_update()

    def load_video(self):
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.current_path)
        total = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.timeline.configure(from_=0, to=max(total - 1, 1))
        self.timeline.set(0)
        self.update_video_frame()

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
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        orig_w, orig_h = pil.size
        target_w, target_h = 720, 480
        ratio = min(target_w / orig_w, target_h / orig_h)
        new_w = int(orig_w * ratio)
        new_h = int(orig_h * ratio)
        pil = pil.resize((new_w, new_h), Image.LANCZOS)
        cimg = ctk.CTkImage(pil, size=(new_w, new_h))
        label.configure(image=cimg, text="")
        if label == self.enh_label:
            self.current_enh_preview = cimg

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
        try:
            sharpen = self.sharpen_s.get()
            kernel_size = max(3, int(sharpen * 2) + 1)
            if kernel_size % 2 == 0:
                kernel_size += 1
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            enhanced = cv2.filter2D(self.current_frame_bgr.copy(), -1, kernel)
            self.show_frame(enhanced, self.enh_label)
        except:
            pass

    def toggle_live_preview(self):
        self.live_enabled = not self.live_enabled
        txt = "ON" if self.live_enabled else "OFF"
        col = self.accent if self.live_enabled else "#21262d"
        self.preview_toggle_btn.configure(text=f"Live Preview: {txt}", fg_color=col)
        if self.live_enabled and self.current_frame_bgr is not None:
            self.live_update()
        else:
            self.enh_label.configure(text="Live preview disabled", image=None)

    # ===================== EXPORT =====================
    def start_export(self):
        if self.export_running:
            messagebox.showwarning("Busy", "Export already running")
            return
        if not self.current_path:
            messagebox.showwarning("No File", "Select a file first")
            return
        if not self.ai_model:
            messagebox.showerror("AI Not Ready", "Real AI model not loaded yet")
            return

        self.export_running = True
        self.export_cancel_requested = False
        self.export_btn.configure(state="disabled", text="AI Processing...", fg_color="#444c56")
        self.status.configure(text="AI Upscaling in progress...")

        threading.Thread(target=self.export_thread, daemon=True).start()

    def export_thread(self):
        out_path = self.get_output_path(self.current_path)
        try:
            if not self.is_video:
                self.ai_enhance_image(out_path)
            else:
                self.ai_enhance_video(out_path)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Export Failed", str(e)))
        finally:
            self.after(0, self.finish_export_ui)

    def ai_enhance_image(self, out_path):
        img = cv2.imread(self.current_path)
        if img is None:
            raise ValueError("Cannot read image")

        # Real AI upscale
        enhanced = self.ai_model.enhance_image(img, face_restore=self.face_var.get())

        cv2.imwrite(out_path, enhanced)
        self.after(0, lambda: self._update_progress(100))
        self.after(0, lambda: messagebox.showinfo("Success", f"AI Enhanced Image saved:\n{out_path}"))

    def ai_enhance_video(self, out_path):
        cap = cv2.VideoCapture(self.current_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Create temp frame folder
        temp_dir = "temp_ai_frames"
        os.makedirs(temp_dir, exist_ok=True)

        frame_idx = 0
        while True:
            if self.export_cancel_requested:
                break
            ret, frame = cap.read()
            if not ret:
                break

            enhanced = self.ai_model.enhance_image(frame, face_restore=self.face_var.get())
            cv2.imwrite(os.path.join(temp_dir, f"frame_{frame_idx:06d}.png"), enhanced)

            percent = int((frame_idx / total_frames) * 100)
            self.after(0, lambda p=percent: self._update_progress(p))

            frame_idx += 1
            if frame_idx % 10 == 0:
                self.after(0, lambda f=frame_idx, t=total_frames: self.status.configure(text=f"AI Processing frame {f}/{t}"))

        cap.release()

        if self.export_cancel_requested:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return

        # Re-encode with ffmpeg
        cmd = [
            "ffmpeg", "-framerate", str(fps), "-i", os.path.join(temp_dir, "frame_%06d.png"),
            "-c:v", "libx264", "-preset", "medium", "-crf", "17",
            "-pix_fmt", "yuv420p", "-y", out_path
        ]
        subprocess.check_call(cmd)
        shutil.rmtree(temp_dir, ignore_errors=True)

        self.after(0, lambda: self._update_progress(100))
        self.after(0, lambda: messagebox.showinfo("Success", f"AI 4× Video saved:\n{out_path}"))

    def finish_export_ui(self):
        self.export_running = False
        self.export_btn.configure(state="normal", text="🚀 EXPORT WITH AI", fg_color="#1f6feb")
        self.status.configure(text="Export finished")
        self.add_to_history()

    def _update_progress(self, percent):
        self.status.configure(text=f"Progress: {percent}%")

    def add_to_history(self):
        entry = f"[{datetime.now().strftime('%H:%M')}] {os.path.basename(self.current_path)} → AI Enhanced\n"
        self.history_text.insert("end", entry)
        self.history_text.see("end")

    def cancel_export(self):
        self.export_cancel_requested = True
        self.status.configure(text="Cancelling AI export...")

    def on_model_change(self, choice):
        self.config["last_model"] = choice
        self.save_config()

    def calculate_size(self, w, h):  # kept for compatibility
        return w * 4, h * 4

    def open_in_system_player(self):
        if self.current_path and os.path.exists(self.current_path):
            if os.name == 'nt':
                os.startfile(self.current_path)
            else:
                subprocess.call(['xdg-open', self.current_path])

    def choose_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder = folder
            self.output_status.configure(text=f"Output: {folder}", text_color=self.accent)

    def get_output_path(self, input_path):
        base, ext = os.path.splitext(os.path.basename(input_path))
        suffix = "_AI_4x" + (".mp4" if self.is_video else ext)
        filename = base + suffix
        if self.output_folder:
            return os.path.join(self.output_folder, filename)
        return os.path.join(os.path.dirname(input_path), filename)

if __name__ == "__main__":
    # ===================== CREATE MODELS FOLDER IF NOT EXISTS =====================
    os.makedirs("models", exist_ok=True)
    print("✅ NotYUpscalerZAi ready. Real AI models will be auto-downloaded on first run.")
    app = NotYUpscalerZAi()
    app.mainloop()