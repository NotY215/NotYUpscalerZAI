# NotYUpscalerZAi.py
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
import time
from moviepy.editor import VideoFileClip
import pygame
import copy

# Models (assuming they exist in models/ folder)
from models.lite_restore import LiteRestoreEnhancer
from models.pro_detail import ProDetailEnhancer
from models.ultra_native import UltraNativeEnhancer
from models.image_enhance import ImageEnhanceModel

try:
    import winsound
    def play_tick(): winsound.Beep(1200, 50)
except ImportError:
    def play_tick(): pass

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

VIDEO_MODELS = {
    "Low (Lite Restore)": LiteRestoreEnhancer,
    "Medium (Pro Detail)": ProDetailEnhancer,
    "High (Ultra Native)": UltraNativeEnhancer
}

IMAGE_MODEL = {
    "Image Enhance": ImageEnhanceModel
}

CONFIG_FILE = "config.json"

class NotYUpscalerZAI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NotYUpscalerZAI")
        self.geometry("1420x920")
        self.minsize(1200, 750)

        if os.path.exists("logo.ico"):
            try:
                self.iconbitmap("logo.ico")
            except:
                pass

        self.accent   = "#00e5ff"
        self.success  = "#00ff9d"
        self.live_enabled = False

        self.current_path = None
        self.is_video = False
        self.cap = None
        self.playing = False
        self.current_frame_bgr = None
        self.output_folder = None

        # Strong references to prevent garbage collection
        self.current_orig_preview = None
        self.current_enh_preview  = None

        self.current_model_dict = VIDEO_MODELS

        # Undo / Redo history for sliders
        self.slider_history = []
        self.history_index = -1

        self.load_config()
        self.detect_specs()

        # Show intro
        self.show_intro_screen()

        # Build UI after intro
        self.create_ui()

def show_intro_screen(self):
    self.intro_win = ctk.CTkToplevel(self)
    self.intro_win.title("")
    self.intro_win.geometry("900x600")
    self.intro_win.overrideredirect(True)
    self.intro_win.configure(fg_color="black")

    # Center
    x = (self.intro_win.winfo_screenwidth() // 2) - 450
    y = (self.intro_win.winfo_screenheight() // 2) - 300
    self.intro_win.geometry(f"900x600+{x}+{y}")

    self.video_label = ctk.CTkLabel(self.intro_win, text="", fg_color="black")
    self.video_label.pack(expand=True, fill="both")

    # Flags
    self.intro_playing = True
    self.intro_audio_done = False

    threading.Thread(target=self.play_intro_with_sound, daemon=True).start()

    # No fixed timeout — close only when video ends


def play_intro_with_sound(self):
    if not os.path.exists("intro.mp4"):
        self.after(0, lambda: self.video_label.configure(text="intro.mp4 not found"))
        self.after(0, self.close_intro)
        return

    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        clip = VideoFileClip("intro.mp4")

        audio_file = "temp_intro_audio.wav"
        if clip.audio:
            clip.audio.write_audiofile(audio_file, logger=None)
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()

        cap = cv2.VideoCapture("intro.mp4")
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30
        delay_ms = int(1000 / fps)

        def update_frame():
            # Safety check: window/label still alive?
            if not self.intro_playing or not cap.isOpened() or not self.video_label.winfo_exists():
                self._cleanup_intro(cap, audio_file)
                return

            ret, frame = cap.read()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil = Image.fromarray(rgb)
                pil = pil.resize((900, 600), Image.Resampling.LANCZOS)
                cimg = ctk.CTkImage(pil, size=(900, 600))
                # Only update if label still exists
                if self.video_label.winfo_exists():
                    self.after(0, lambda i=cimg: self._safe_configure_label(i))
                self.after(delay_ms, update_frame)
            else:
                # Video ended
                self._cleanup_intro(cap, audio_file)

        self.after(delay_ms, update_frame)

    except Exception as e:
        print("Intro error:", str(e))
        self.after(0, lambda: self.video_label.configure(text=f"Playback error: {str(e)}"))
        self.after(1500, self.close_intro)


def _safe_configure_label(self, cimg):
    """Safe update — check existence before configure"""
    if hasattr(self, 'video_label') and self.video_label.winfo_exists():
        self.video_label.configure(image=cimg)


def _cleanup_intro(self, cap, audio_file):
    try:
        cap.release()
        pygame.mixer.music.stop()
        pygame.mixer.quit()

        # Wait a tiny bit and try to delete audio file
        time.sleep(0.4)
        if os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except PermissionError:
                print("Could not delete temp audio file — still in use")
    except:
        pass

    self.after(0, self.close_intro)


def close_intro(self):
    self.intro_playing = False
    if hasattr(self, 'intro_win') and self.intro_win.winfo_exists():
        self.intro_win.destroy()

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
        # ── Top bar ────────────────────────────────────────────────
        top = ctk.CTkFrame(self, height=60, fg_color="#0f172a")
        top.pack(fill="x")
        top.pack_propagate(False)

        if os.path.exists("logo.ico"):
            try:
                logo = Image.open("logo.ico").resize((38,38), Image.LANCZOS)
                logo_ctk = ctk.CTkImage(logo, size=(38,38))
                ctk.CTkLabel(top, image=logo_ctk, text="").pack(side="left", padx=16, pady=10)
            except:
                pass

        ctk.CTkLabel(top, text="NotYUpscalerZAI", font=("Segoe UI", 26, "bold"),
                     text_color=self.accent).pack(side="left", padx=8, pady=10)

        # ── Main content ───────────────────────────────────────────
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=8)

        content.grid_columnconfigure(0, weight=7)
        content.grid_columnconfigure(1, weight=3)
        content.grid_rowconfigure(0, weight=1)

        # Left – Preview area
        left = ctk.CTkFrame(content, fg_color="#0f172a", corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,8), pady=0)

        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)

        preview_frame = ctk.CTkFrame(left, fg_color="transparent")
        preview_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(1, weight=1)
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(1, weight=0)
        preview_frame.grid_rowconfigure(2, weight=0)

        # Original
        orig_panel = ctk.CTkFrame(preview_frame, fg_color="transparent")
        orig_panel.grid(row=0, column=0, sticky="nsew", padx=(0,6))
        ctk.CTkLabel(orig_panel, text="Original", font=("Segoe UI",16,"bold")).pack()
        self.orig_label = ctk.CTkLabel(orig_panel, text="Select media", width=640, height=400,
                                       fg_color="#1e293b", corner_radius=8)
        self.orig_label.pack(pady=8, expand=True, fill="both")

        # Enhanced
        enh_panel = ctk.CTkFrame(preview_frame, fg_color="transparent")
        enh_panel.grid(row=0, column=1, sticky="nsew", padx=(6,0))
        ctk.CTkLabel(enh_panel, text="Enhanced", font=("Segoe UI",16,"bold"),
                     text_color=self.accent).pack()
        self.enh_label = ctk.CTkLabel(enh_panel, text="Live preview disabled", width=640, height=400,
                                      fg_color="#1e293b", corner_radius=8)
        self.enh_label.pack(pady=8, expand=True, fill="both")

        # Timeline + buttons
        ctrl_bar = ctk.CTkFrame(preview_frame, fg_color="#0f172a")
        ctrl_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8,4))

        self.play_btn = ctk.CTkButton(ctrl_bar, text="▶ Play", width=100,
                                      command=lambda: self.toggle_play())
        self.play_btn.pack(side="left", padx=12)

        self.timeline = ctk.CTkSlider(ctrl_bar, from_=0, to=100,
                                      command=lambda v: self.on_timeline_change(v),
                                      height=24, button_length=32)
        self.timeline.pack(side="left", fill="x", expand=True, padx=12)

        ctk.CTkButton(ctrl_bar, text="Open in Player", width=140,
                      command=lambda: self.open_in_system_player()).pack(side="right", padx=12)

        # Bottom buttons (Export / Cancel)
        bottom_ctrl = ctk.CTkFrame(preview_frame, fg_color="#0f172a")
        bottom_ctrl.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4,8))

        ctk.CTkButton(bottom_ctrl, text="Export", fg_color=self.success, text_color="black",
                      command=lambda: self.start_export()).pack(side="left", padx=8, fill="x", expand=True)

        ctk.CTkButton(bottom_ctrl, text="Cancel", fg_color="#e74c3c", command=self.quit).pack(side="right", padx=8)

        self.info_label = ctk.CTkLabel(preview_frame, text="No file loaded", font=("Segoe UI",13),
                                       text_color="gray")
        self.info_label.grid(row=3, column=0, columnspan=2, pady=6)

        # ── Right sidebar ──────────────────────────────────────────
        right = ctk.CTkFrame(content, fg_color="#1e293b", corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(8,0))

        ctk.CTkButton(right, text="📂  Select Image / Video",
                      command=lambda: self.select_file(),
                      fg_color=self.accent, text_color="black", height=48,
                      font=("Segoe UI",15,"bold")).pack(pady=20, padx=24, fill="x")

        self.file_name = ctk.CTkLabel(right, text="No file selected", text_color="gray")
        self.file_name.pack(pady=6)

        ctk.CTkButton(right, text="📁  Choose Output Folder",
                      command=lambda: self.choose_output_folder(),
                      fg_color="#4a6bff", height=42).pack(pady=10, padx=24, fill="x")

        self.output_status = ctk.CTkLabel(right, text="Output: same folder", text_color="gray")
        self.output_status.pack(pady=4)

        self.specs_btn = ctk.CTkButton(right, text="🔍  Read PC Specs",
                                       command=lambda: self.read_specs(),
                                       fg_color="#7b00ff", height=40)
        if not self.config.get("specs_read", False):
            self.specs_btn.pack(pady=16, padx=24, fill="x")

        self.device_frame = ctk.CTkFrame(right, fg_color="transparent")
        if self.config.get("specs_read", False):
            self.device_frame.pack(pady=12, padx=24, fill="x")

        ctk.CTkLabel(self.device_frame, text="Device").pack(anchor="w")
        self.device_var = ctk.StringVar(value=self.config.get("preferred_device", "Auto"))
        ctk.CTkOptionMenu(self.device_frame, values=["Auto", "GPU (if available)", "CPU only"],
                          variable=self.device_var, fg_color="#7b00ff").pack(fill="x", pady=6)

        ctk.CTkLabel(right, text="Model").pack(anchor="w", padx=24, pady=(16,4))
        self.model_var = ctk.StringVar(value=list(self.current_model_dict.keys())[0])
        self.model_menu = ctk.CTkOptionMenu(right, values=list(self.current_model_dict.keys()),
                                            variable=self.model_var, command=lambda v: self.live_update(),
                                            fg_color="#7b00ff")
        self.model_menu.pack(padx=24, pady=4, fill="x")

        ctk.CTkLabel(right, text="Target Resolution").pack(anchor="w", padx=24, pady=(16,4))
        self.target_var = ctk.StringVar(value="Fit 2K")
        ctk.CTkOptionMenu(right, values=["Fit 2K","Fit 3K","Fit 4K"],
                          variable=self.target_var, fg_color="#7b00ff").pack(padx=24, pady=4, fill="x")

        self.preview_toggle_btn = ctk.CTkButton(right, text="Live Preview: DISABLED",
                                                fg_color="gray30", text_color="white",
                                                command=lambda: self.toggle_live_preview(),
                                                height=48)
        self.preview_toggle_btn.pack(pady=24, padx=24, fill="x")

        # Adjustments (hidden for videos)
        self.adj_frame = ctk.CTkFrame(right, fg_color="#16213e")
        self.adj_frame.pack(pady=16, padx=24, fill="x")
        ctk.CTkLabel(self.adj_frame, text="Adjustments", font=("Segoe UI",15,"bold")).pack(pady=10)

        self.sharpen_s   = self._add_slider(self.adj_frame, "Sharpen",   0.5, 4.0, 2.2)
        self.contrast_s  = self._add_slider(self.adj_frame, "Contrast",  0.7, 2.0, 1.35)
        self.sat_s       = self._add_slider(self.adj_frame, "Saturation",0.5, 2.0, 1.15)
        self.glow_s      = self._add_slider(self.adj_frame, "Glow",      0.0, 1.2, 0.4)

        # Undo / Redo buttons
        hist_bar = ctk.CTkFrame(right, fg_color="transparent")
        hist_bar.pack(pady=12, padx=24, fill="x")

        ctk.CTkButton(hist_bar, text="Undo (Ctrl+Z)", width=120,
                      command=lambda: self.undo()).pack(side="left", padx=6)
        ctk.CTkButton(hist_bar, text="Redo (Ctrl+Y)", width=120,
                      command=lambda: self.redo()).pack(side="right", padx=6)

        self.export_btn = ctk.CTkButton(right, text="Export Enhanced File",
                                        command=lambda: self.start_export(),
                                        fg_color=self.success, text_color="black", height=60,
                                        font=("Segoe UI",18,"bold"))
        self.export_btn.pack(pady=32, padx=24, fill="x")

        self.status = ctk.CTkLabel(right, text="", text_color=self.accent)
        self.status.pack(pady=8)

        # Bind Ctrl+Z / Ctrl+Y
        self.bind_all("<Control-z>", lambda e: self.undo())
        self.bind_all("<Control-y>", lambda e: self.redo())

    def _add_slider(self, parent, text, minv, maxv, defv):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(f, text=text, width=100, anchor="w").pack(side="left")
        s = ctk.CTkSlider(f, from_=minv, to=maxv, command=self.live_update)
        s.set(defv)
        s.pack(side="right", fill="x", expand=True, padx=12)
        return s

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("Media","*.jpg *.jpeg *.png *.webp *.mp4 *.mkv *.avi *.mov")])
        if not path: return

        self.current_path = path
        self.is_video = path.lower().endswith(('.mp4','.mkv','.avi','.mov'))
        self.file_name.configure(text=os.path.basename(path)[:45])

        if self.is_video:
            self.current_model_dict = VIDEO_MODELS
            self.adj_frame.pack_forget()
            default = list(VIDEO_MODELS.keys())[1]   # Medium by default
        else:
            self.current_model_dict = IMAGE_MODEL
            self.adj_frame.pack(pady=16, padx=24, fill="x")
            default = "Image Enhance"

        self.model_var.set(default)
        self.model_menu.configure(values=list(self.current_model_dict.keys()))

        self.push_history()  # initial state

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
        self.info_label.configure(text=f"{w}×{h} → {target_w}×{target_h}")
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
            self.after(40, self.update_video_frame)

    def show_frame(self, bgr, label):
        if bgr is None: return
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        pil = pil.resize((640,400), Image.LANCZOS)
        cimg = ctk.CTkImage(pil, size=(640,400))
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
            model_cls = self.current_model_dict[self.model_var.get()]
            model = model_cls(
                sharpen   = self.sharpen_s.get(),
                contrast  = self.contrast_s.get(),
                saturation= self.sat_s.get(),
                glow      = self.glow_s.get()
            )
            enhanced = model.enhance_frame(self.current_frame_bgr.copy())
            self.show_frame(enhanced, self.enh_label)
            self.push_history()
            play_tick()
        except Exception as e:
            print("Live preview error:", str(e))

    def push_history(self):
        state = {
            "sharpen":   self.sharpen_s.get(),
            "contrast":  self.contrast_s.get(),
            "saturation":self.sat_s.get(),
            "glow":      self.glow_s.get()
        }
        # Remove future states
        self.slider_history = self.slider_history[:self.history_index+1]
        self.slider_history.append(state)
        self.history_index += 1

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            state = self.slider_history[self.history_index]
            self.sharpen_s.set(state["sharpen"])
            self.contrast_s.set(state["contrast"])
            self.sat_s.set(state["saturation"])
            self.glow_s.set(state["glow"])
            self.live_update()

    def redo(self):
        if self.history_index < len(self.slider_history) - 1:
            self.history_index += 1
            state = self.slider_history[self.history_index]
            self.sharpen_s.set(state["sharpen"])
            self.contrast_s.set(state["contrast"])
            self.sat_s.set(state["saturation"])
            self.glow_s.set(state["glow"])
            self.live_update()

    def toggle_live_preview(self):
        self.live_enabled = not self.live_enabled
        txt = "ENABLED" if self.live_enabled else "DISABLED"
        col = "#00e5ff" if self.live_enabled else "gray20"
        self.preview_toggle_btn.configure(text=f"Live Preview: {txt}", fg_color=col)
        if self.live_enabled and self.current_frame_bgr is not None:
            self.live_update()
        elif not self.live_enabled:
            self.enh_label.configure(text="Live preview disabled", image=None)

    def start_export(self):
        if not self.current_path:
            messagebox.showwarning("No file", "Please select a file first")
            return
        threading.Thread(target=self.export_thread, daemon=True).start()

    def export_thread(self):
        self.export_btn.configure(state="disabled")
        self.status.configure(text="Exporting... please wait")

        try:
            out_path = self.get_output_path(self.current_path)
            model_cls = self.current_model_dict[self.model_var.get()]
            model = model_cls(
                sharpen=self.sharpen_s.get(),
                contrast=self.contrast_s.get(),
                saturation=self.sat_s.get(),
                glow=self.glow_s.get()
            )

            if not self.is_video:
                img = cv2.imread(self.current_path)
                if img is None:
                    raise ValueError("Cannot read input image")
                h, w = img.shape[:2]
                nw, nh = self.calculate_size(w, h)
                up = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
                enhanced = model.enhance_frame(up)
                if not cv2.imwrite(out_path, enhanced):
                    raise RuntimeError("Failed to save image")
            else:
                cap = cv2.VideoCapture(self.current_path)
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                nw, nh = self.calculate_size(w, h)
                vf = model.get_ffmpeg_vf(nw, nh) if hasattr(model, 'get_ffmpeg_vf') else f"scale={nw}:{nh}"
                vf = f"minterpolate=fps=60:mi_mode=blend,{vf}"

                cmd = [
                    "ffmpeg", "-y", "-i", self.current_path,
                    "-vf", vf,
                    "-r", "60",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                    "-c:a", "aac", "-b:a", "192k",
                    out_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print("FFmpeg stderr:\n", result.stderr)
                    raise RuntimeError(f"FFmpeg failed (code {result.returncode})")

            self.after(0, lambda: messagebox.showinfo("Success", f"File saved:\n{out_path}"))
            self.after(300, lambda p=out_path: self.auto_open_output(p))
        except Exception as e:
            self.after(0, lambda msg=str(e): messagebox.showerror("Export Failed", msg))
        finally:
            self.after(0, lambda: [
                self.export_btn.configure(state="normal"),
                self.status.configure(text="")
            ])

    # ── Helper methods ──────────────────────────────────────────────

    def choose_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_status.configure(text=f"Output: {os.path.basename(folder)}", text_color=self.accent)

    def get_output_path(self, input_path):
        base, ext = os.path.splitext(os.path.basename(input_path))
        name = f"{base}_enhanced{ext}"
        if self.output_folder and os.path.isdir(self.output_folder):
            return os.path.join(self.output_folder, name)
        return os.path.join(os.path.dirname(input_path), name)

    def read_specs(self):
        txt = f"{self.ram_gb:.1f} GB RAM • {self.cores} cores • {'CUDA' if self.has_cuda else 'No GPU'}"
        self.status.configure(text=txt)
        self.specs_btn.pack_forget()
        self.device_frame.pack(pady=12, padx=24, fill="x")
        self.device_var.set(self.recommended)
        self.config["specs_read"] = True
        self.save_config()

    def calculate_size(self, w, h):
        t = self.target_var.get()
        targets = {"Fit 2K": (2560,1440), "Fit 3K": (2880,1620), "Fit 4K": (3840,2160)}
        tw, th = targets.get(t, (2560,1440))
        scale = min(tw / w, th / h)
        return int(w * scale // 2 * 2), int(h * scale // 2 * 2)

    def open_in_system_player(self):
        if self.current_path and os.path.exists(self.current_path):
            if os.name == 'nt':
                os.startfile(self.current_path)
            else:
                subprocess.call(['xdg-open' if os.name == 'posix' else 'open', self.current_path])

    def auto_open_output(self, path):
        if os.path.exists(path):
            try:
                if os.name == 'nt':
                    os.startfile(path)
                else:
                    subprocess.call(['xdg-open' if os.name == 'posix' else 'open', path])
            except:
                pass

if __name__ == "__main__":
    app = NotYUpscalerZAI()
    app.mainloop()