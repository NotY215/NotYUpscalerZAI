import PyInstaller.__main__
import os, sys, shutil, subprocess, time

# --- 1. ENVIRONMENT SETUP ---
def prepare_environment(venv_name="venv"):
    if sys.prefix != sys.base_prefix:
        try:
            from PIL import Image
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
        return 
    
    venv_python = os.path.join(os.getcwd(), venv_name, "Scripts", "python.exe") if os.name == "nt" else \
                  os.path.join(os.getcwd(), venv_name, "bin", "python")

    if os.path.exists(venv_python):
        subprocess.run([venv_python] + sys.argv); sys.exit()

prepare_environment("venv")

# --- 2. GENERATE PROFESSIONAL MULTI-RES ICON ---
def create_pro_icon(png_path, ico_output):
    from PIL import Image
    if not os.path.exists(png_path):
        print(f"Error: {png_path} not found!"); sys.exit(1)
    
    print(f"Generating high-res icon...")
    img = Image.open(png_path).convert("RGBA")
    
    # CRITICAL: This list ensures Windows has a pixel-perfect match for every view.
    # The 256x256 layer is what makes it "stretch" to the edges in large view.
    icon_sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
    img.save(ico_output, sizes=icon_sizes, bitmap_format="png") # 'png' format inside ICO is modern standard
    return ico_output

# --- 3. CLEANUP & BUILD ---
# Change the 'dist' folder name each time to force Windows to refresh the icon cache
build_id = int(time.time())
dist_path = f"dist_v{build_id}"

for folder in ['build', 'dist']:
    if os.path.exists(folder): shutil.rmtree(folder, ignore_errors=True)

script_main = "NotYUpscale.py"
png_icon = "logo.png"
generated_ico = "final_icon.ico"
models_data = "models;models" if os.name == "nt" else "models:models"

icon_file = create_pro_icon(png_icon, generated_ico)

PyInstaller.__main__.run([
    script_main,
    "--onefile",
    "--windowed",
    f"--icon={icon_file}",
    f"--add-data={models_data}",
    f"--distpath={dist_path}", # Forces a fresh icon refresh in Windows Explorer
    "--noconfirm",
    "--clean"
])

print(f"\nSUCCESS! High-quality build is in: {dist_path}")
