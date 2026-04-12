"""
py2app setup script for Todo Manager
Build command:  python setup.py py2app
"""
from setuptools import setup

APP = ["todo_manager.py"]

OPTIONS = {
    "argv_emulation": False,
    "iconfile": None,          # replace with "icon.icns" if you have one
    "plist": {
        "CFBundleName":             "Todo Manager",
        "CFBundleDisplayName":      "Todo Manager",
        "CFBundleIdentifier":       "com.aphadke.todomanager",
        "CFBundleVersion":          "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHumanReadableCopyright": "© 2025 Abhijit Phadke",
        "LSMinimumSystemVersion":   "10.13.0",
        "NSHighResolutionCapable":  True,
    },
    "packages": [],
    "excludes": ["email", "http", "urllib", "xml", "unittest", "pydoc"],
}

setup(
    name="Todo Manager",
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
