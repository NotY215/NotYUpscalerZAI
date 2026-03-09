# build_exe.py
# Fixed version: proper quoting + Windows-compatible --add-data syntax

import PyInstaller.__main__
import os
import sys
import shutil
import subprocess

# ─────────────────────────────────────────────────────────────
# Ensure running inside venv
# ─────────────────────────────────────────────────────────────
def ensure_venv(venv="venv"):
    if sys.prefix != sys.base_prefix:
        return
    if os.name == "nt":
        py = os.path.join(venv, "Scripts", "python.exe")
    else:
        py = os.path.join(venv, "bin", "python")

    if os.path.exists(py):
        subprocess.run([py] + sys.argv)
        sys.exit(0)
    else:
        print("❌ Virtual environment not found!")
        sys.exit(1)

ensure_venv()

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
SCRIPT      = "main.py"
ICON_FILE   = "logo.ico"
MODELS_DIR  = "models"
FFMPEG_DIR  = "ffmpeg"
DIST        = r"F:\Own Apps\Installer"

os.makedirs(DIST, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# ICON CHECK
# ─────────────────────────────────────────────────────────────
if not os.path.exists(ICON_FILE):
    print("❌ ERROR: logo.ico not found!")
    sys.exit(1)

print(f"Using icon: {ICON_FILE}")

# ─────────────────────────────────────────────────────────────
# COLLECT ALL ADD-DATA ITEMS (properly quoted for Windows)
# ─────────────────────────────────────────────────────────────
add_data_args = []

# Separator: ; on Windows, : on Unix
sep = ";" if os.name == "nt" else ":"

# 1. Models folder (recursive)
if os.path.exists(MODELS_DIR):
    print("Adding models folder contents...")
    for root, dirs, files in os.walk(MODELS_DIR):
        if "__pycache__" in root:
            continue
        for file in files:
            full_path = os.path.join(root, file).replace("\\", "/")  # normalize to forward slashes
            rel_path = os.path.relpath(root, ".").replace("\\", "/")
            # Quote the whole argument to prevent splitting
            arg = f"--add-data={full_path}{sep}{rel_path}"
            add_data_args.append(arg)
            print(f"  Added: {full_path} → {rel_path}")
else:
    print("⚠ Warning: models folder not found")

# 2. Bundled ffmpeg files
if os.path.exists(FFMPEG_DIR):
    print("Adding FFmpeg binaries...")
    for file in ["ffmpeg.exe", "ffprobe.exe"]:
        src = os.path.join(FFMPEG_DIR, file).replace("\\", "/")
        if os.path.exists(src):
            arg = f"--add-data={src}{sep}."
            add_data_args.append(arg)
            print(f"  Added: {src} → .")
        else:
            print(f"⚠ Warning: {file} not found in ffmpeg folder")
else:
    print("⚠ Warning: ffmpeg folder not found — building without bundled FFmpeg!")

# 3. Icon file
icon_arg = f"--add-data={ICON_FILE}{sep}."
add_data_args.append(icon_arg)

# ─────────────────────────────────────────────────────────────
# PYINSTALLER ARGUMENTS
# ─────────────────────────────────────────────────────────────
args = [
    SCRIPT,
    "--onefile",
    "--windowed",
    "--name=NotYUpscalerZAI",
    f"--icon={ICON_FILE}",
    "--collect-all=cv2",
    "--collect-all=psutil",
    "--collect-all=customtkinter",
    "--collect-all=PIL",
    "--hidden-import=cv2",
    *add_data_args,
    f"--distpath={DIST}",
    "--noconfirm",
    "--clean",
    "--noupx",
    "--log-level=WARN"
]

print("\nPyInstaller command:")
print("pyinstaller " + " ".join(args))
print("-" * 100)

# ─────────────────────────────────────────────────────────────
# BUILD
# ─────────────────────────────────────────────────────────────
try:
    print("🚀 Starting build...")
    PyInstaller.__main__.run(args)
    print("\n✅ Build finished successfully!")
except Exception as e:
    print(f"\n❌ Build failed: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────────────────────
print("\n🧹 Cleaning up build files...")

folders_to_delete = ['build', '__pycache__']
spec_file = f"{SCRIPT.replace('.py', '')}.spec"

for folder in folders_to_delete:
    if os.path.exists(folder):
        shutil.rmtree(folder, ignore_errors=True)

if os.path.exists(spec_file):
    os.remove(spec_file)

# ─────────────────────────────────────────────────────────────
# FINAL STATUS
# ─────────────────────────────────────────────────────────────
exe_name = SCRIPT.replace(".py", ".exe")
exe = os.path.join(DIST, exe_name)

print("\n" + "=" * 100)
if os.path.exists(exe):
    print("🎉 BUILD SUCCESSFUL!")
    print(f"EXE location: {exe}")
    print("Size increased by ~50–70 MB (bundled FFmpeg)")
    print("\nIf icon doesn't show correctly:")
    print("  1. Delete the old .exe")
    print("  2. Restart Windows Explorer (or PC)")
    print("  3. Rebuild if needed")
else:
    print("❌ BUILD FAILED — check output above")
print("=" * 100)

input("\nPress Enter to exit...")