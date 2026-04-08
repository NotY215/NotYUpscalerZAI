#!/usr/bin/env python3
"""
Build script for NotYUpscalerZAi using Nuitka
Run: python build.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build_dirs():
    """Clean previous build directories"""
    dirs_to_clean = ['build', 'dist', 'main.build', 'main.dist', 'NotYUpscalerZAi.dist', 'NotYUpscalerZAi.build']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Removing {dir_name}...")
            try:
                shutil.rmtree(dir_name, ignore_errors=True)
            except:
                pass

def copy_ffmpeg_to_dist():
    """Copy ffmpeg executables to dist folder"""
    ffmpeg_dir = Path('ffmpeg')
    dist_dir = Path('dist/NotYUpscalerZAi.dist')
    
    if ffmpeg_dir.exists() and dist_dir.exists():
        print("\nCopying ffmpeg files...")
        # Create ffmpeg folder in dist
        ffmpeg_dist = dist_dir / 'ffmpeg'
        ffmpeg_dist.mkdir(exist_ok=True)
        
        for ff_file in ffmpeg_dir.glob('*'):
            if ff_file.is_file():
                shutil.copy2(ff_file, ffmpeg_dist / ff_file.name)
                print(f"  Copied: ffmpeg/{ff_file.name}")

def copy_models_to_dist():
    """Copy models folder to dist"""
    models_dir = Path('models')
    dist_models = Path('dist/NotYUpscalerZAi.dist/models')
    
    if models_dir.exists():
        print("Copying models...")
        if dist_models.exists():
            shutil.rmtree(dist_models)
        shutil.copytree(models_dir, dist_models, ignore=shutil.ignore_patterns('__pycache__'))
        print("  Models copied successfully")

def copy_icons_to_dist():
    """Copy icon files to dist"""
    icon_files = ['logo.ico', 'logo.png']
    dist_dir = Path('dist/NotYUpscalerZAi.dist')
    
    for icon in icon_files:
        if os.path.exists(icon):
            shutil.copy2(icon, dist_dir / icon)
            print(f"  Copied: {icon}")

def move_executable():
    """Move the generated executable to the correct location"""
    # Check different possible locations for the generated exe
    possible_locations = [
        Path('dist/main.dist/NotYUpscalerZAi.exe'),
        Path('dist/NotYUpscalerZAi.dist/NotYUpscalerZAi.exe'),
        Path('NotYUpscalerZAi.exe'),
        Path('main.dist/NotYUpscalerZAi.exe'),
    ]
    
    for location in possible_locations:
        if location.exists():
            # Ensure dist directory exists
            Path('dist').mkdir(exist_ok=True)
            target = Path('dist/NotYUpscalerZAi.exe')
            shutil.move(str(location), str(target))
            print(f"\nMoved executable to: {target}")
            return True
    
    # If not found, try to find any exe in dist folders
    for pattern in ['dist/*.exe', 'dist/*/*.exe', '*.exe']:
        import glob
        for exe_file in glob.glob(pattern):
            if 'NotYUpscalerZAi' in exe_file or 'main' in exe_file:
                target = Path('dist/NotYUpscalerZAi.exe')
                shutil.move(exe_file, str(target))
                print(f"\nMoved executable from {exe_file} to: {target}")
                return True
    
    return False

def build_with_nuitka():
    """Build executable using Nuitka"""
    
    # Create a temporary main.py for building if needed
    if not os.path.exists('main.py'):
        print("Error: main.py not found!")
        return False
    
    # Nuitka build command for standalone onefile executable
    cmd = [
        sys.executable, '-m', 'nuitka',
        '--standalone',
        '--onefile',
        '--enable-plugin=tk-inter',
        '--include-package=customtkinter',
        '--include-package=cv2',
        '--include-package=numpy',
        '--include-package=PIL',
        '--include-package=psutil',
        '--include-module=models',
        '--include-data-dir=models=models',
        '--include-data-files=logo.ico=logo.ico',
        '--include-data-files=logo.png=logo.png',
        f'--windows-icon-from-ico={os.path.abspath("logo.ico")}',
        '--windows-console-mode=disable',
        '--windows-uac-admin',
        '--product-name=NotYUpscalerZAi',
        '--product-version=7.1.0',
        '--file-description=AI Video & Image Upscaler',
        '--copyright=NotY Studios',
        '--output-dir=dist',
        '--output-filename=NotYUpscalerZAi.exe',
        '--remove-output',
        'main.py'
    ]
    
    print("=" * 60)
    print("Building NotYUpscalerZAi with Nuitka")
    print("=" * 60)
    print("\nThis may take 5-10 minutes...\n")
    print("Command being run:")
    print(" ".join(cmd))
    print("\n" + "=" * 60 + "\n")
    
    try:
        # Run the build process
        result = subprocess.run(cmd, cwd=os.getcwd(), check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error: {e}")
        return False

def create_portable_zip():
    """Create a portable zip of the application"""
    import zipfile
    from datetime import datetime
    
    dist_dir = Path('dist/NotYUpscalerZAi.dist')
    if not dist_dir.exists():
        print("\nDist directory not found, checking for standalone exe...")
        # If only the exe exists, create a simple zip with just the exe
        exe_file = Path('dist/NotYUpscalerZAi.exe')
        if exe_file.exists():
            zip_path = Path('dist/NotYUpscalerZAi_Portable.zip')
            print(f"\nCreating portable zip with executable: {zip_path}")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(exe_file, 'NotYUpscalerZAi.exe')
                print(f"  Added: NotYUpscalerZAi.exe")
            return
    
    # Create full portable zip with all files
    zip_path = Path('dist/NotYUpscalerZAi_Portable.zip')
    print(f"\nCreating portable zip: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in dist_dir.rglob('*'):
            if file.is_file():
                # Preserve directory structure
                arcname = file.relative_to(dist_dir.parent)
                zipf.write(file, arcname)
                print(f"  Added: {arcname}")
    
    print(f"\nPortable zip created: {zip_path}")

def verify_build():
    """Verify that the executable was created successfully"""
    exe_paths = [
        Path('dist/NotYUpscalerZAi.exe'),
        Path('dist/NotYUpscalerZAi.dist/NotYUpscalerZAi.exe'),
        Path('NotYUpscalerZAi.exe'),
    ]
    
    for exe_path in exe_paths:
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\n✓ Executable found: {exe_path}")
            print(f"  Size: {size_mb:.2f} MB")
            return True
    
    # Try to find any exe in the dist folder
    if Path('dist').exists():
        for exe_file in Path('dist').glob('**/*.exe'):
            if 'NotYUpscalerZAi' in exe_file.name or 'main' in exe_file.name:
                size_mb = exe_file.stat().st_size / (1024 * 1024)
                print(f"\n✓ Executable found: {exe_file}")
                print(f"  Size: {size_mb:.2f} MB")
                return True
    
    return False

def main():
    """Main build function"""
    print("NotYUpscalerZAi Build Script v2.0")
    print("=" * 60)
    
    # Check if required files exist
    required_files = ['main.py', 'logo.ico', 'logo.png']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print(f"Error: Missing required files: {', '.join(missing_files)}")
        print("Make sure you're running this script from the correct directory!")
        return
    
    # Check if ffmpeg folder exists
    if not Path('ffmpeg').exists():
        print("Warning: ffmpeg folder not found!")
        print("Make sure to add ffmpeg.exe, ffplay.exe, ffprobe.exe in the ffmpeg folder")
    
    # Check if models folder has __init__.py
    if not Path('models/__init__.py').exists():
        print("Error: models/__init__.py is missing!")
        print("Please create models/__init__.py file")
        return
    
    # Install/Update Nuitka
    print("\nChecking Nuitka installation...")
    try:
        subprocess.run([sys.executable, '-m', 'nuitka', '--version'], 
                      capture_output=True, check=True)
        print("Nuitka is already installed")
    except:
        print("Installing Nuitka...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'nuitka'], check=True)
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'ordered-set', 'zstandard'], check=True)
    
    # Clean previous builds
    print("\nCleaning previous builds...")
    clean_build_dirs()
    
    # Build with Nuitka
    if build_with_nuitka():
        print("\n" + "=" * 60)
        print("Build completed!")
        print("=" * 60)
        
        # Move executable if needed
        move_executable()
        
        # Copy additional files
        print("\nCopying additional files...")
        copy_models_to_dist()
        copy_ffmpeg_to_dist()
        copy_icons_to_dist()
        
        # Verify build
        if verify_build():
            # Create portable zip
            create_portable_zip()
            
            print("\n" + "=" * 60)
            print("BUILD SUMMARY")
            print("=" * 60)
            print("\n✓ Standalone executable created successfully!")
            print("\nLocations:")
            
            exe_file = Path('dist/NotYUpscalerZAi.exe')
            if exe_file.exists():
                print(f"  • Standalone EXE: {exe_file.absolute()}")
            
            dist_folder = Path('dist/NotYUpscalerZAi.dist')
            if dist_folder.exists():
                print(f"  • Distribution folder: {dist_folder.absolute()}")
            
            zip_file = Path('dist/NotYUpscalerZAi_Portable.zip')
            if zip_file.exists():
                print(f"  • Portable ZIP: {zip_file.absolute()}")
            
            print("\n" + "=" * 60)
            print("NEXT STEPS")
            print("=" * 60)
            print("\n1. Test the executable by running: dist/NotYUpscalerZAi.exe")
            print("2. The executable includes all dependencies")
            print("3. Distribute the EXE file or the entire dist folder")
            print("\nNote: First run may be slow as it extracts files")
        else:
            print("\n⚠ Warning: Could not verify executable location")
            print("Check the 'dist' folder manually for the executable")
    else:
        print("\n❌ Build failed! Check the errors above.")
        print("\nTroubleshooting tips:")
        print("1. Make sure Visual C++ Build Tools are installed")
        print("2. Run: pip install --upgrade nuitka")
        print("3. Try building without --onefile flag first")
        sys.exit(1)

if __name__ == "__main__":
    main()