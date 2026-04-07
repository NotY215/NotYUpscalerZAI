import os
import sys

# PyInstaller one-file builder for NotYUpscalerZAI v7.1
# Run this with: python build_exe.py

script_name = "main.py"   # Make sure your main file is named this
exe_name = "NotYUpscalerZAI_v7.1"

print("Starting build for NotY Upscaler ZAI v7.1...")

cmd = [
    "pyinstaller",
    "--onefile",
    "--windowed",
    f"--name={exe_name}",
    "--icon=logo.ico" if os.path.exists("logo.ico") else "",
    "--add-data=ffmpeg.exe;.",
    "--add-data=models;models",
    "--hidden-import=customtkinter",
    "--hidden-import=cv2",
    "--hidden-import=PIL.Image",
    "--hidden-import=psutil",
    "--hidden-import=re",
    "--clean",
    script_name
]

cmd = [x for x in cmd if x]

print("Running command:")
print(" ".join(cmd))

os.system(" ".join(cmd))

print("\nBuild completed!")
print(f"EXE is in: dist/{exe_name}.exe")

print("\n=== Right-Click Context Menu Setup ===")
print("1. Copy the EXE to a permanent folder (e.g. C:\\Programs\\NotYUpscalerZAI)")
print("2. Create a file named add_context.reg with the content below and run it as Administrator.")

exe_full_path = os.path.abspath(f"dist/{exe_name}.exe").replace("\\", "\\\\")

reg_content = f'''Windows Registry Editor Version 5.00

[HKEY_CLASSES_ROOT\\*\\shell\\NotYUpscalerZAI]
@="Upscale with NotY Upscaler ZAI"
"Icon"="\\"{exe_full_path}\\""

[HKEY_CLASSES_ROOT\\*\\shell\\NotYUpscalerZAI\\command]
@="\\"{exe_full_path}\\" \\"%1\\""
'''

print("\n--- Paste this into add_context.reg ---")
print(reg_content)
print("---------------------------------------")

input("\nPress Enter to exit...")