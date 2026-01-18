import PyInstaller.__main__
import shutil
import os


FOLDER_RELEASE = "release"
PLATFORM = "window"

FINAL_PATH = FOLDER_RELEASE + "\\" + PLATFORM

PATH = os.path.dirname(os.path.realpath(__file__))

def build():
    args = [
        'src\\main.py',
        '--onedir',
        '--console',
        '--clean',
        '-y',
        '--name=laetus',
        f'--version-file={PATH}\\version.txt',
        f'--distpath={FINAL_PATH}', 
        '--workpath=build_temp',
        '--specpath=build_temp',
        f'--add-binary', 'C:\Program Files\LLVM\\bin\clang.exe;clang\\bin',
        f'--add-binary', 'C:\Program Files\LLVM\\bin\*.dll;clang\\bin',
        f'--add-data', 'C:\Program Files\LLVM\lib;clang\\lib',
    ]

    try:
        print("START BUILDING 🛠️")
        PyInstaller.__main__.run(args)
        if os.path.exists("build_temp"):
            shutil.rmtree("build_temp")
        print("FINISHED BUILDING ✅")

    except Exception as e:
        print(f"FAILED TO BUILD ❌: {e}")

if __name__ == "__main__":
    build()