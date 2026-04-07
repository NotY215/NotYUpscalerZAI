import os
import sys
from pathlib import Path

# PyInstaller one-file builder for NotYUpscalerZAI with bundled ffmpeg.exe and models
# Run this script with: python build_exe.py

script_name = "notyupscalerzai.py"  # Your main file name
exe_name = "NotYUpscalerZAI_v7.1"

print("Starting build for NotYUpscalerZAI v7.1...")

cmd = [
    "pyinstaller",
    "--onefile",
    "--windowed",
    "--name=NotYUpscalerZAI_v7.1",
    f"--name={exe_name}",
    "--icon=logo.ico" if os.path.exists("logo.ico") else "",
    "--add-data=ffmpeg.exe;.",
    "--add-data=models;models",
    "--hidden-import=customtkinter",
    "--hidden-import=cv2",
    "--hidden-import=PIL",
    "--hidden-import=psutil",
    "--hidden-import=tkinter.dnd",
    "--collect-all=customtkinter",
    "--clean",
    script_name
]

# Remove empty strings
cmd = [x for x in cmd if x]

print("Running command:")
print(" ".join(cmd))

os.system(" ".join(cmd))

print("\nBuild completed!")
print(f"EXE should be in the 'dist' folder: dist/{exe_name}.exe")
print("\nTo add Right-Click 'Upscale with NotY Upscaler ZAI':")
print("1. Place the .exe in a permanent folder (e.g. C:\\NotYUpscalerZAI)")
print("2. Run the .exe once (it will register paths)")
print("3. For full context menu, create a .reg file with the following content and run it as Administrator:")

reg_content = f'''Windows Registry Editor Version 5.00

[HKEY_CLASSES_ROOT\\*\\shell\\NotYUpscalerZAI]
@="Upscale with NotY Upscaler ZAI"
"Icon"="\"{os.path.abspath(f'dist/{exe_name}.exe')}\""

[HKEY_CLASSES_ROOT\\*\\shell\\NotYUpscalerZAI\\command]
@="\"{os.path.abspath(f'dist/{exe_name}.exe')}\" \"%1\""
'''

print("\n--- Copy below into a file named 'add_context.reg' and double-click it (as Admin) ---")
print(reg_content)
print("---------------------------------------------------")

input("\nPress Enter to exit...")