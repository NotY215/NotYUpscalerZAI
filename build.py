# build_exe.py
# Full production build script with proper icon + packages + models

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
ICON_FILE   = "logo.ico"   # MUST be .ico for taskbar icon
MODELS      = "models"
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
# ADD MODELS RECURSIVELY
# ─────────────────────────────────────────────────────────────
add_data_args = []

if os.path.exists(MODELS):
    for root, dirs, files in os.walk(MODELS):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(root, ".")
            add_data_args.append(f'--add-data={full_path};{rel_path}')
else:
    print("⚠ Warning: models folder not found")

# Add icon to package (for runtime use)
add_data_args.append(f'--add-data={ICON_FILE};.')

# ─────────────────────────────────────────────────────────────
# PYINSTALLER ARGUMENTS
# ─────────────────────────────────────────────────────────────
args = [
    SCRIPT,
    "--onefile",
    "--windowed",

    # Proper EXE icon (window + taskbar)
    f"--icon={ICON_FILE}",

    # Collect required packages fully
    "--collect-all=cv2",
    "--collect-all=psutil",
    "--collect-all=customtkinter",
    "--collect-all=PIL",

    # Safety for OpenCV
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
print("-" * 70)

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
exe = os.path.join(DIST, SCRIPT.replace(".py", ".exe"))

print("\n" + "=" * 70)
if os.path.exists(exe):
    print("🎉 BUILD SUCCESSFUL!")
    print(f"EXE location: {exe}")
    print("\nIf icon appears incorrect:")
    print("1. Delete old .exe")
    print("2. Restart Windows Explorer or restart PC")
    print("3. Rebuild again")
else:
    print("❌ BUILD FAILED — check output above")
print("=" * 70)

input("\nPress Enter to exit...")