import sys
from cx_Freeze import setup, Executable

# Dependencies
build_exe_options = {
    "packages": [
        "os", "sys", "PyQt5", "vlc", "logging", 
        "json", "pathlib", "difflib", "textblob"
    ],
    "include_files": [
        ("data/", "data/"),  # Copy data folder
        ("assets/", "assets/"),  # Copy assets nếu có
        ("README.md", "README.md"),
        ("LICENSE", "LICENSE")
    ],
    "excludes": []
}

base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="Dictation Practice",
    version="1.0",
    description="An application for practicing English dictation",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "main.py",
            base=base,
            icon="assets/icon.ico",  # Thêm icon cho ứng dụng
            target_name="DictationPractice.exe"
        )
    ]
) 