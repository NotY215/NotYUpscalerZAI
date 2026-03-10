# build_exe.py
# Improved version: cleaner model/FFmpeg inclusion, proper quoting, Windows-friendly

import PyInstaller.__main__
import os
import sys
import shutil
import subprocess

# ─────────────────────────────────────────────────────────────
# Force run inside virtual environment
# ─────────────────────────────────────────────────────────────
def ensure_venv(venv="venv"):
    if sys.prefix != sys.base_prefix:
        return True
    if os.name == "nt":
        py = os.path.join(venv, "Scripts", "python.exe")
    else:
        py = os.path.join(venv, "bin", "python")

    if os.path.exists(py):
        print(f"Restarting inside venv: {py}")
        subprocess.run([py] + sys.argv, check=False)
        sys.exit(0)
    else:
        print("❌ Virtual environment not found!")
        sys.exit(1)

ensure_venv()

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────
SCRIPT      = "main.py"                     # Your main application file
ICON_FILE   = "logo.ico"                    # Must exist in current folder
MODELS_DIR  = "models"                      # Folder with enhancer modules
FFMPEG_DIR  = "ffmpeg"                      # Folder with ffmpeg.exe + ffprobe.exe
DIST_DIR    = r"F:\Own Apps\Installer\NotyUpscalerZAI"

os.makedirs(DIST_DIR, exist_ok=True)

# Separator for --add-data (Windows = ;    Linux/macOS = :)
ADD_DATA_SEP = ";" if os.name == "nt" else ":"

# ─────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────
if not os.path.isfile(SCRIPT):
    print(f"❌ ERROR: Main script not found: {SCRIPT}")
    sys.exit(1)

if not os.path.isfile(ICON_FILE):
    print(f"❌ ERROR: Icon file not found: {ICON_FILE}")
    sys.exit(1)

print(f"Using icon: {ICON_FILE}")

# ─────────────────────────────────────────────────────────────
# COLLECT --add-data ITEMS
# ─────────────────────────────────────────────────────────────
add_data = []

# 1. Entire models folder → put inside 'models' in the bundle
if os.path.isdir(MODELS_DIR):
    print("Adding models folder...")
    add_data.append(f"--add-data={MODELS_DIR}{ADD_DATA_SEP}models")
    # Optional: list what was found (for debugging)
    for root, _, files in os.walk(MODELS_DIR):
        for f in files:
            if not f.endswith(('.pyc', '.pyo')):
                print(f"  included: {os.path.join(root, f)}")
else:
    print("⚠  Warning: 'models' folder not found — continuing without it")

# 2. FFmpeg binaries → place in root of bundle
if os.path.isdir(FFMPEG_DIR):
    print("Adding FFmpeg binaries...")
    for bin_name in ["ffmpeg.exe", "ffprobe.exe"]:
        src = os.path.join(FFMPEG_DIR, bin_name)
        if os.path.isfile(src):
            add_data.append(f"--add-data={src}{ADD_DATA_SEP}.")
            print(f"  included: {src}")
        else:
            print(f"⚠  Missing: {src}")
else:
    print("⚠  Warning: 'ffmpeg' folder not found → exe will use system FFmpeg if available")

# ─────────────────────────────────────────────────────────────
# PYINSTALLER ARGUMENTS
# ─────────────────────────────────────────────────────────────
pyi_args = [
    SCRIPT,
    "--onefile",
    "--windowed",                   # No console window
    "--name=NotYUpscalerZAI",
    f"--icon={ICON_FILE}",
    "--collect-all=cv2",
    "--collect-all=psutil",
    "--collect-all=customtkinter",
    "--collect-all=PIL",            # Pillow
    "--collect-all=numpy",          # often needed with cv2
    "--hidden-import=cv2",
    "--hidden-import=customtkinter",
    "--hidden-import=PIL",
    *add_data,                      # models + ffmpeg
    f"--distpath={DIST_DIR}",
    "--noconfirm",
    "--clean",
    "--noupx",                      # modern PyInstaller recommends against UPX
    "--log-level=WARN"
]

print("\nPyInstaller command being executed:")
print("pyinstaller " + " ".join(pyi_args))
print("─" * 100)

# ─────────────────────────────────────────────────────────────
# RUN BUILD
# ─────────────────────────────────────────────────────────────
try:
    print("🚀 Starting PyInstaller build...")
    PyInstaller.__main__.run(pyi_args)
    print("\n✅ PyInstaller finished")
except Exception as e:
    print(f"\n❌ PyInstaller crashed: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
# CLEANUP TEMPORARY FILES
# ─────────────────────────────────────────────────────────────
print("\n🧹 Cleaning temporary build files...")

for path in ["build", f"{SCRIPT.replace('.py', '')}.spec"]:
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        else:
            os.remove(path)

# ─────────────────────────────────────────────────────────────
# FINAL RESULT CHECK
# ─────────────────────────────────────────────────────────────
exe_name = "NotYUpscalerZAI.exe"
exe_path = os.path.join(DIST_DIR, exe_name)

print("\n" + "═" * 100)
if os.path.isfile(exe_path):
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print("🎉 BUILD APPEARS SUCCESSFUL!")
    print(f"Output file : {exe_path}")
    print(f"Size        : {size_mb:.1f} MB")
    print("\nTips if icon is missing:")
    print("  • Delete old .exe first")
    print("  • Restart File Explorer (or PC)")
    print("  • Clear icon cache: ie4uinit.exe -show")
else:
    print("❌ BUILD FAILED — executable not found")
    print("Check the output above for errors (especially missing modules or binaries)")
print("═" * 100)

input("\nPress Enter to close...")