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

# Models
from models.lite_restore import LiteRestoreEnhancer
from models.pro_detail import ProDetailEnhancer
from models.ultra_native import UltraNativeEnhancer
from models.image_enhance import ImageEnhanceModel

try:
    import winsound
    def play_tick(): winsound.Beep(1200, 50)
except:
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

        self.accent = "#00e5ff"
        self.success = "#00ff9d"
        self.live_enabled = True

        self.current_path = None
        self.is_video = False
        self.cap = None
        self.playing = False
        self.current_frame_bgr = None
        self.output_folder = None
        self.current_preview_image = None  # Strong reference fix

        self.current_model_dict = VIDEO_MODELS
        self.adjustment_frame = None  # Will be created dynamically

        self.load_config()
        self.detect_specs()
        self.create_ui()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                self.config = json.load(f)
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
        top_bar = ctk.CTkFrame(self, height=60, fg_color="#0f172a")
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        if os.path.exists("logo.ico"):
            try:
                logo_pil = Image.open("logo.ico").resize((38, 38), Image.LANCZOS)
                logo_img = ctk.CTkImage(logo_pil, size=(38, 38))
                ctk.CTkLabel(top_bar, image=logo_img, text="").pack(side="left", padx=18, pady=10)
            except:
                pass

        ctk.CTkLabel(top_bar, text="NotYUpscalerZAI", font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=self.accent).pack(side="left", padx=8, pady=10)

        scroll = ctk.CTkScrollableFrame(self, fg_color="#1a1f2e")
        scroll.pack(fill="both", expand=True, padx=15, pady=10)

        main = ctk.CTkFrame(scroll, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=10, pady=10)

        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=1)

        # Preview Area
        preview_area = ctk.CTkFrame(main, fg_color="#0f172a", corner_radius=12)
        preview_area.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        preview_area.grid_columnconfigure(0, weight=1)
        preview_area.grid_columnconfigure(1, weight=1)

        orig_box = ctk.CTkFrame(preview_area, fg_color="transparent")
        orig_box.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(orig_box, text="Original", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=6)
        self.orig_label = ctk.CTkLabel(orig_box, text="Select media", width=640, height=400,
                                       fg_color="#1e2937", corner_radius=8)
        self.orig_label.pack(pady=8)

        enh_box = ctk.CTkFrame(preview_area, fg_color="transparent")
        enh_box.grid(row=0, column=1, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(enh_box, text="Enhanced", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=self.accent).pack(pady=6)
        self.enh_label = ctk.CTkLabel(enh_box, text="Live preview will appear here", width=640, height=400,
                                      fg_color="#1e2937", corner_radius=8)
        self.enh_label.pack(pady=8)

        timeline_frame = ctk.CTkFrame(preview_area, fg_color="#0f172a")
        timeline_frame.grid(row=1, column=0, columnspan=2, padx=15, pady=(5,8), sticky="ew")

        self.play_btn = ctk.CTkButton(timeline_frame, text="▶ Play", width=100, height=38, command=self.toggle_play)
        self.play_btn.pack(side="left", padx=15)

        self.timeline = ctk.CTkSlider(timeline_frame, from_=0, to=100, command=self.on_timeline_change,
                                      height=28, button_length=36)
        self.timeline.pack(side="left", fill="x", expand=True, padx=15, pady=8)
        self.timeline.set(0)

        ctk.CTkButton(timeline_frame, text="Open in System Player", width=160, height=38,
                      command=self.open_in_system_player).pack(side="right", padx=15)

        self.info_label = ctk.CTkLabel(preview_area, text="No file loaded", font=ctk.CTkFont(size=13),
                                       text_color="gray")
        self.info_label.grid(row=2, column=0, columnspan=2, pady=8)

        # Bottom copyright
        bottom_bar = ctk.CTkFrame(self, height=30, fg_color="#0f172a")
        bottom_bar.pack(fill="x", side="bottom")
        ctk.CTkLabel(bottom_bar, text="GNU Copyright By NotY215", font=ctk.CTkFont(size=12),
                     text_color="gray").pack(pady=6)

        # Sidebar
        sidebar = ctk.CTkFrame(main, fg_color="#1e293b", corner_radius=12)
        sidebar.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkButton(sidebar, text="📂 Select Image or Video",
                      command=self.select_file,
                      fg_color=self.accent, text_color="black", height=48,
                      font=ctk.CTkFont(size=15, weight="bold")).pack(pady=20, padx=25, fill="x")

        self.file_name = ctk.CTkLabel(sidebar, text="No file selected", text_color="gray")
        self.file_name.pack(pady=8)

        ctk.CTkButton(sidebar, text="📁 Choose Output Folder",
                      command=self.choose_output_folder,
                      fg_color="#4a6bff", height=42).pack(pady=12, padx=25, fill="x")

        self.output_status = ctk.CTkLabel(sidebar, text="Output: Same as input", text_color="gray")
        self.output_status.pack(pady=4, padx=25)

        self.specs_btn = ctk.CTkButton(sidebar, text="🔍 Read PC Specs",
                                       command=self.read_specs,
                                       fg_color="#7b00ff", height=40)
        if not self.config.get("specs_read", False):
            self.specs_btn.pack(pady=15, padx=25, fill="x")

        self.device_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        if self.config.get("specs_read", False):
            self.device_frame.pack(pady=10, padx=25, fill="x")

        ctk.CTkLabel(self.device_frame, text="Processing Device").pack(anchor="w")
        self.device_var = ctk.StringVar(value=self.config.get("preferred_device", "Auto"))
        ctk.CTkOptionMenu(self.device_frame, values=["Auto", "GPU (if available)", "CPU only"],
                          variable=self.device_var, fg_color="#7b00ff").pack(fill="x", pady=5)

        ctk.CTkLabel(sidebar, text="AI Model").pack(anchor="w", padx=25, pady=(15,5))
        self.model_var = ctk.StringVar(value=list(self.current_model_dict.keys())[0])
        self.model_menu = ctk.CTkOptionMenu(sidebar, values=list(self.current_model_dict.keys()),
                                            variable=self.model_var, command=self.live_update,
                                            fg_color="#7b00ff")
        self.model_menu.pack(padx=25, pady=5, fill="x")

        ctk.CTkLabel(sidebar, text="Target Resolution").pack(anchor="w", padx=25, pady=(15,5))
        self.target_var = ctk.StringVar(value="Fit 2K")
        ctk.CTkOptionMenu(sidebar, values=["Fit 2K", "Fit 3K", "Fit 4K"],
                          variable=self.target_var, fg_color="#7b00ff").pack(padx=25, pady=5, fill="x")

        self.preview_toggle_btn = ctk.CTkButton(sidebar, text="Live Preview: ENABLED",
                                                fg_color="#00e5ff", text_color="black",
                                                command=self.toggle_live_preview, height=45)
        self.preview_toggle_btn.pack(pady=25, padx=25, fill="x")

        # Adjustments frame (will be shown/hidden based on file type)
        self.adjustment_frame = ctk.CTkFrame(sidebar, fg_color="#16213e")
        self.adjustment_frame.pack(pady=15, padx=25, fill="x")
        ctk.CTkLabel(self.adjustment_frame, text="Adjustments", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=10)

        self.sharpen_s   = self.add_slider(self.adjustment_frame, "Sharpen",   0.5, 4.0, 2.2)
        self.contrast_s  = self.add_slider(self.adjustment_frame, "Contrast",  0.7, 2.0, 1.35)
        self.sat_s       = self.add_slider(self.adjustment_frame, "Saturation",0.5, 2.0, 1.15)
        self.glow_s      = self.add_slider(self.adjustment_frame, "Glow",      0.0, 1.2, 0.4)

        self.export_btn = ctk.CTkButton(sidebar, text="Export Enhanced File",
                                        command=self.start_export,
                                        fg_color=self.success, text_color="black", height=60,
                                        font=ctk.CTkFont(size=18, weight="bold"))
        self.export_btn.pack(pady=30, padx=25, fill="x")

        self.status = ctk.CTkLabel(sidebar, text="", text_color=self.accent)
        self.status.pack()

    def add_slider(self, parent, text, minv, maxv, defv):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(f, text=text, width=90).pack(side="left")
        s = ctk.CTkSlider(f, from_=minv, to=maxv, command=self.live_update)
        s.set(defv)
        s.pack(side="right", fill="x", expand=True, padx=10)
        return s

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
        self.status.configure(text=f"{self.ram_gb:.1f} GB • {self.cores} cores • {'CUDA' if self.has_cuda else 'No GPU'}")
        self.specs_btn.pack_forget()
        self.device_frame.pack(pady=10, padx=25, fill="x")
        self.device_var.set(self.recommended)
        self.config["specs_read"] = True
        self.save_config()

    def toggle_live_preview(self):
        self.live_enabled = not self.live_enabled
        if self.live_enabled:
            self.preview_toggle_btn.configure(text="Live Preview: ENABLED", fg_color="#00e5ff")
            if self.current_frame_bgr is not None:
                self.live_update()
        else:
            self.preview_toggle_btn.configure(text="Live Preview: DISABLED", fg_color="gray20")
            self.enh_label.configure(text="Live preview disabled", image=None)

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("Media", "*.jpg *.jpeg *.png *.webp *.mp4 *.mkv *.avi *.mov")])
        if not path: return
        self.current_path = path
        self.is_video = path.lower().endswith(('.mp4','.mkv','.avi','.mov'))
        self.file_name.configure(text=os.path.basename(path)[:45])

        if self.is_video:
            self.current_model_dict = VIDEO_MODELS
            default = "High (Ultra Native)"
            self.adjustment_frame.pack_forget()   # Hide adjustments for video
        else:
            self.current_model_dict = IMAGE_MODEL
            default = "Image Enhance"
            self.adjustment_frame.pack(pady=15, padx=25, fill="x")  # Show for image

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
        self.info_label.configure(text=f"Image: {w}x{h} → Target: {target_w}x{target_h}")
        self.live_update()

    def load_video(self):
        if self.cap: self.cap.release()
        self.cap = cv2.VideoCapture(self.current_path)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Cannot open video")
            return
        total = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
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
        pil = pil.resize((640, 400), Image.LANCZOS)
        cimg = ctk.CTkImage(pil, size=(640, 400))
        label.configure(image=cimg, text="")
        self.current_preview_image = cimg  # Strong reference

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
                sharpen=self.sharpen_s.get(),
                contrast=self.contrast_s.get(),
                saturation=self.sat_s.get(),
                glow=self.glow_s.get()
            )
            enhanced = model.enhance_frame(self.current_frame_bgr.copy())
            self.show_frame(enhanced, self.enh_label)
            play_tick()
        except Exception as e:
            print("Live preview error:", str(e))

    def start_export(self):
        if not self.current_path:
            messagebox.showwarning("No file", "Select a file first")
            return
        threading.Thread(target=self.export_thread, daemon=True).start()

    def export_thread(self):
        self.export_btn.configure(state="disabled")
        self.status.configure(text="Exporting...")

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
                    raise ValueError("Cannot read image")
                h, w = img.shape[:2]
                nw, nh = self.calculate_size(w, h)
                up = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
                enhanced = model.enhance_frame(up)
                cv2.imwrite(out_path, enhanced)
            else:
                cap = cv2.VideoCapture(self.current_path)
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                nw, nh = self.calculate_size(w, h)
                vf = model.get_ffmpeg_vf(nw, nh) if hasattr(model, 'get_ffmpeg_vf') else f"scale={nw}:{nh}"
                vf = f"minterpolate=fps=60:mi_mode=blend,{vf}"

                cmd = [
                    "ffmpeg", "-i", self.current_path,
                    "-vf", vf,
                    "-r", "60",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                    "-c:a", "aac", "-b:a", "192k",
                    "-y", out_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(f"FFmpeg failed:\n{result.stderr[:400]}")

            self.after(0, lambda: messagebox.showinfo("Success", f"Saved to:\n{out_path}"))
            self.after(200, lambda: self.auto_open_output(out_path))
        except Exception as e:
            self.after(0, lambda msg=str(e): messagebox.showerror("Export Failed", msg))
        finally:
            self.after(0, lambda: [
                self.export_btn.configure(state="normal"),
                self.status.configure(text="Ready")
            ])

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