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
import math
import sys
from io import BytesIO

# Auto-install missing packages
for pkg in ["ffmpeg-python", "google-api-python-client", "google-auth-oauthlib", "google-auth-httplib2"]:
    try:
        __import__(pkg.replace("-", "_"))
    except ImportError:
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

import ffmpeg
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

# Check real ffmpeg binary
def find_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except:
        return False

if not find_ffmpeg():
    print("WARNING: ffmpeg not found in PATH.")
    print("Download: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip")
    print("Add 'bin' folder to PATH, restart terminal, then run again.")

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
TOKEN_FILE = "token.json"
CLIENT_FILE = "client.json"  # You must create this from Google Cloud Console

SCOPES = ['https://www.googleapis.com/auth/drive']

class NotYUpscalerZAI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NotY Upscaler ZAI")
        self.geometry("1480x960")
        self.minsize(1280, 800)

        if os.path.exists("logo.ico"):
            try:
                self.iconbitmap("logo.ico")
            except Exception as e:
                print("Logo load failed:", e)

        self.configure(fg_color="#0d1117")

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

        self.drive_service = None
        self.credentials = None

        self.mode = "Local"  # Default

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
        top = ctk.CTkFrame(self, height=64, fg_color="#161b22", corner_radius=0)
        top.pack(fill="x")
        top.pack_propagate(False)

        ctk.CTkLabel(top, text="NotY Upscaler ZAI", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=self.accent).pack(side="left", padx=24, pady=12)

        self.mode_local = ctk.CTkButton(top, text="Local", fg_color=self.accent, text_color="#000000",
                                        height=42, width=120, command=lambda: self.set_mode("Local"))
        self.mode_local.pack(side="left", padx=8)

        self.mode_online = ctk.CTkButton(top, text="Online", fg_color="#21262d", text_color="#8b949e",
                                         height=42, width=120, command=lambda: self.set_mode("Online"))
        self.mode_online.pack(side="left", padx=8)

        self.login_btn = ctk.CTkButton(top, text="Login to Google", fg_color="#238636", height=42, width=160,
                                       command=self.login_google)
        self.login_btn.pack(side="right", padx=24)

        self.specs_label = ctk.CTkLabel(top, text=f"RAM: {self.ram_gb:.1f} GB • Cores: {self.cores} • {'CUDA' if self.has_cuda else 'CPU'}",
                                        font=ctk.CTkFont(size=13), text_color="#8b949e")
        self.specs_label.pack(side="right", padx=16)

        content = ctk.CTkFrame(self, fg_color="#0d1117")
        content.pack(fill="both", expand=True)

        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=0)

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
                                      font=ctk.CTkFont(size=14), command=self.toggle_play)
        self.play_btn.pack(side="left", padx=8)

        self.timeline = ctk.CTkSlider(ctrl, from_=0, to=100, command=self.on_timeline_change,
                                      height=24, button_length=32, fg_color="#21262d", progress_color=self.accent)
        self.timeline.pack(side="left", fill="x", expand=True, padx=12)
        self.timeline.set(0)

        ctk.CTkButton(ctrl, text="Open in Player", width=140, height=42,
                      command=self.open_in_system_player).pack(side="right", padx=8)

        self.info_label = ctk.CTkLabel(left, text="No file loaded", font=ctk.CTkFont(size=13),
                                       text_color="#8b949e")
        self.info_label.grid(row=2, column=0, columnspan=2, pady=8)

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

    def set_mode(self, mode):
        self.mode = mode
        if mode == "Local":
            self.mode_local.configure(fg_color=self.accent, text_color="#000000")
            self.mode_online.configure(fg_color="#21262d", text_color="#8b949e")
        else:
            self.mode_local.configure(fg_color="#21262d", text_color="#8b949e")
            self.mode_online.configure(fg_color=self.accent, text_color="#000000")
            if not self.drive_service:
                self.login_google()

    def login_google(self):
        if not os.path.exists(CLIENT_FILE):
            messagebox.showerror("Missing client.json", "client.json not found.\n\nCreate it from:\nhttps://console.cloud.google.com/apis/credentials\n(Enable Drive API, OAuth 2.0 Client ID, Desktop app)")
            return

        scopes = SCOPES
        if os.path.exists(TOKEN_FILE):
            self.credentials = Credentials.from_authorized_user_file(TOKEN_FILE, scopes)
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                except RefreshError:
                    os.remove(TOKEN_FILE)
                    self.credentials = None

        if not self.credentials:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_FILE, scopes)
            self.credentials = flow.run_local_server(port=0)
            with open(TOKEN_FILE, 'w') as token:
                token.write(self.credentials.to_json())

        self.drive_service = build('drive', 'v3', credentials=self.credentials)
        self.login_btn.configure(text="Logged In", fg_color=self.success, state="disabled")
        messagebox.showinfo("Success", "Logged in to Google Drive")

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
            cap_temp = cv2.VideoCapture(path)
            if cap_temp.isOpened():
                w = int(cap_temp.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap_temp.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap_temp.release()
                self.info_label.configure(text=f"Video: {w}×{h}")
            else:
                self.info_label.configure(text="Video loaded")
        else:
            frame = cv2.imread(path)
            if frame is not None:
                h, w = frame.shape[:2]
                self.info_label.configure(text=f"Image: {w}×{h}")
            else:
                self.info_label.configure(text="Image loaded")

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

        orig_w, orig_h = pil.size
        target_w, target_h = 680, 460
        ratio = min(target_w / orig_w, target_h / orig_h)
        new_w = int(orig_w * ratio)
        new_h = int(orig_h * ratio)
        pil = pil.resize((new_w, new_h), Image.LANCZOS)

        cimg = ctk.CTkImage(pil, size=(new_w, new_h))
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
            kernel_size = max(3, int(sharpen * 2) + 1)
            if kernel_size % 2 == 0:
                kernel_size += 1
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
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
            messagebox.showwarning("Already Exporting", "An export is already running.")
            return

        if not self.current_path:
            messagebox.showwarning("No file", "Please select a file first")
            return

        if self.mode == "Online" and not self.drive_service:
            messagebox.showwarning("Login Required", "Please login to Google first for Online mode.")
            return

        self.disable_buttons(True)

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

    def disable_buttons(self, disable):
        state = "disabled" if disable else "normal"
        self.play_btn.configure(state=state)
        self.export_btn.configure(state=state)
        self.preview_toggle_btn.configure(state=state)
        self.mode_local.configure(state=state)
        self.mode_online.configure(state=state)
        self.login_btn.configure(state=state)
        self.model_menu.configure(state=state)
        # OptionMenu doesn't support state=disabled, so we rely on export_running check

    def export_thread(self):
        out_path = self.get_output_path(self.current_path)

        try:
            if self.mode == "Local":
                self.local_export(out_path)
            else:
                self.online_export(out_path)
        except Exception as e:
            self.after(0, lambda msg=str(e): messagebox.showerror("Export Failed", msg))
        finally:
            self.after(0, self._finish_export_ui)

    def local_export(self, out_path):
        if not self.is_video:
            img = cv2.imread(self.current_path)
            if img is None:
                raise ValueError("Cannot read image")
            h, w = img.shape[:2]
            nw, nh = self.calculate_size(w, h)
            up = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
            sharpen = self.sharpen_s.get()
            kernel_size = max(3, int(sharpen * 2) + 1)
            if kernel_size % 2 == 0:
                kernel_size += 1
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            enhanced = cv2.filter2D(up, -1, kernel)
            if not cv2.imwrite(out_path, enhanced):
                raise RuntimeError("cv2.imwrite failed")
            self.after(0, lambda: self._update_progress(100))
        else:
            cap = cv2.VideoCapture(self.current_path)
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()

            nw, nh = self.calculate_size(w, h)

            target_res = self.target_var.get()
            if "4K" in target_res:
                video_bitrate = 45000
                audio_bitrate = 320
            elif "3K" in target_res:
                video_bitrate = 30000
                audio_bitrate = 256
            else:
                video_bitrate = 18000
                audio_bitrate = 192

            sharpen = self.sharpen_s.get()
            vf = f"scale={nw}:{nh}:flags=lanczos,unsharp=7:7:{sharpen*1.8}"

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
                    self.after(0, lambda: messagebox.showinfo("Cancelled", "Export cancelled."))
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
                err = self.export_process.stderr.read()
                raise RuntimeError(f"FFmpeg failed:\n{err[:400]}")

            if not self.export_cancel_requested:
                self.after(0, lambda: self._update_progress(100))
                self.after(0, lambda: messagebox.showinfo("Success", f"Exported to:\n{out_path}"))

    def online_export(self, out_path):
        if not self.drive_service:
            raise RuntimeError("Not logged in to Google")

        file_size_mb = os.path.getsize(self.current_path) / (1024*1024)
        if file_size_mb > 500:
            raise ValueError(f"File size {file_size_mb:.1f} MB exceeds 500 MB limit for Online mode")

        self.status.configure(text="Uploading video to Drive...")
        video_id = self.upload_to_drive(self.current_path, "video")

        self.status.configure(text="Creating Colab notebook...")
        notebook_code = self.generate_colab_notebook(video_id)
        notebook_path = "temp_colab_notebook.ipynb"
        with open(notebook_path, "w", encoding="utf-8") as f:
            f.write(notebook_code)
        notebook_id = self.upload_to_drive(notebook_path, "notebook")
        os.remove(notebook_path)

        colab_link = f"https://colab.research.google.com/drive/{notebook_id}"
        self.status.configure(text="Colab ready. Open link below and run all cells.")
        messagebox.showinfo("Colab Ready", f"Open this link in your browser:\n{colab_link}\n\nRun all cells in Colab.\nAfter finish, click 'Check for Output' in this app.")

        self.export_btn.configure(text="Check for Output", state="normal", fg_color=self.accent,
                                  command=lambda: self.check_online_output(out_path))

    def upload_to_drive(self, path, file_type):
        metadata = {
            'name': os.path.basename(path),
            'mimeType': 'application/octet-stream' if file_type == "video" else 'application/vnd.google.colaboratory'
        }
        media = MediaFileUpload(path, resumable=True)
        file = self.drive_service.files().create(body=metadata, media_body=media, fields='id').execute()
        return file.get('id')

    def generate_colab_notebook(self, video_id):
        sharpen = self.sharpen_s.get()
        kernel_size = max(3, int(sharpen * 2) + 1)
        if kernel_size % 2 == 0:
            kernel_size += 1

        notebook_json = {
            "nbformat": 4,
            "nbformat_minor": 0,
            "metadata": {"colab": {"name": "NotYUpscalerZAI Colab", "provenance": []}},
            "cells": [
                {
                    "cell_type": "markdown",
                    "source": ["# NotY Upscaler ZAI - Colab\nRun all cells below."]
                },
                {
                    "cell_type": "code",
                    "source": [
                        "!pip install opencv-python-headless\n",
                        "import cv2\n",
                        "import numpy as np\n",
                        "from google.colab import drive\n",
                        "drive.mount('/content/drive')\n",
                        "video_path = '/content/drive/MyDrive/" + os.path.basename(self.current_path) + "'\n",
                        "out_path = '/content/drive/MyDrive/" + os.path.basename(self.get_output_path(self.current_path)) + "'\n",
                        "cap = cv2.VideoCapture(video_path)\n",
                        "w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))\n",
                        "h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))\n",
                        "cap.release()\n",
                        "nw, nh = " + str(self.calculate_size(int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))) + "\n",
                        "vf = f'scale={nw}:{nh}:flags=lanczos,unsharp=7:7:" + str(sharpen*1.8) + "'\n",
                        "!ffmpeg -i \"{video_path}\" -vf \"$vf\" -c:v libx264 -preset medium -crf 17 -c:a aac -b:a 192k -y \"{out_path}\"\n",
                        "print('Done! Output saved to:', out_path)\n"
                    ]
                }
            ]
        }
        return json.dumps(notebook_json, indent=2)

    def check_online_output(self, out_path):
        base = os.path.basename(out_path)
        files = self.drive_service.files().list(q=f"name='{base}'", fields="files(id, name)").execute()
        items = files.get('files', [])
        if items:
            file_id = items[0]['id']
            self.download_from_drive(file_id, out_path)
            self.drive_service.files().delete(fileId=file_id).execute()
            messagebox.showinfo("Success", f"Downloaded to:\n{out_path}")
            self._finish_export_ui()
        else:
            messagebox.showinfo("Waiting", "Output not found yet. Run Colab again and wait a bit.")

    def download_from_drive(self, file_id, out_path):
        request = self.drive_service.files().get_media(fileId=file_id)
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        with open(out_path, 'wb') as f:
            f.write(fh.getvalue())

    def cancel_export(self):
        if not self.export_running:
            return
        self.export_cancel_requested = True
        self.status.configure(text="Cancelling...", text_color=self.danger)
        self.progress_label.configure(text="Cancelling...")

        if self.mode == "Local" and self.export_process:
            self.export_process.terminate()
            time.sleep(0.5)
            if os.path.exists(self.get_output_path(self.current_path)):
                os.remove(self.get_output_path(self.current_path))

        self._finish_export_ui()
        messagebox.showinfo("Cancelled", "Export cancelled.")

    def _finish_export_ui(self):
        self.export_running = False
        self.export_cancel_requested = False
        self.export_process = None
        self.export_btn.configure(state="normal", text="Export", fg_color="#1f6feb")
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()
        self.cancel_btn.pack_forget()
        self.status.configure(text="Export finished")
        self.disable_buttons(False)

    def _update_progress(self, percent):
        if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
            self.progress_bar.set(percent / 100.0)
            self.progress_label.configure(text=f"{percent}%")

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
        filename = f"{base}_enhanced{ext if not self.is_video else '.mp4'}"
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