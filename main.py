import PyInstaller.__main__
import os, sys, shutil, subprocess, time

# --- 1. ENVIRONMENT SETUP ---
def prepare_environment(venv_name="venv"):
    if sys.prefix != sys.base_prefix:
        return 
    
    venv_python = os.path.join(os.getcwd(), venv_name, "Scripts", "python.exe") if os.name == "nt" else \
                  os.path.join(os.getcwd(), venv_name, "bin", "python")

    if os.path.exists(venv_python):
        subprocess.run([venv_python] + sys.argv); sys.exit()

prepare_environment("venv")

# --- 2. CONFIGURATION ---
TARGET_DIR = r"F:\Own Apps\Installer" # Your specified path
script_main = "NotYUpscalerZAi.py"
png_icon = "logo.png"
generated_ico = "final_icon.ico"
models_data = "models;models" if os.name == "nt" else "models:models"

# Ensure the target directory exists
if not os.path.exists(TARGET_DIR):
    os.makedirs(TARGET_DIR)

# --- 3. GENERATE ICON ---
def create_pro_icon(png_path, ico_output):
    from PIL import Image
    if not os.path.exists(png_path):
        print(f"Error: {png_path} not found!"); sys.exit(1)
    
    print(f"Generating high-res icon...")
    img = Image.open(png_path).convert("RGBA")
    icon_sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
    img.save(ico_output, sizes=icon_sizes, bitmap_format="png")
    return ico_output

icon_file = create_pro_icon(png_icon, generated_ico)

# --- 4. RUN PYINSTALLER ---
PyInstaller.__main__.run([
    script_main,
    "--onefile",
    "--windowed",
    f"--icon={icon_file}",
    f"--add-data={models_data}",
    f"--distpath={TARGET_DIR}", # Directs EXE to your F: drive path
    "--noconfirm",
    "--clean"
])

# --- 5. AGGRESSIVE CLEANUP ---
print("\nCleaning up all build artifacts...")

# List of files/folders to remove from the current directory
spec_file = script_main.replace(".py", ".spec")
to_remove = ["build", "dist", "__pycache__", generated_ico, spec_file]

for item in to_remove:
    if os.path.exists(item):
        if os.path.isdir(item):
            shutil.rmtree(item, ignore_errors=True)
        else:
            os.remove(item)

print(f"\nDONE!")
print(f"Your EXE is located at: {TARGET_DIR}")
print("All temporary build files have been deleted.")
