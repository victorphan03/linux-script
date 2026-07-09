"""
Test script to check if pystray works on this machine.
Run this directly: python test_tray.py
"""
import sys
import os

print("Python:", sys.executable)
print("Version:", sys.version)

try:
    import pystray
    print(f"pystray: OK (loaded)")
except ImportError:
    print("ERROR: pystray is NOT installed!")
    print("Run: pip install pystray pillow")
    input("Press Enter to exit...")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw
    import PIL
    print(f"Pillow version: {PIL.__version__}")
except ImportError:
    print("ERROR: Pillow is NOT installed!")
    print("Run: pip install pillow")
    input("Press Enter to exit...")
    sys.exit(1)

print("\nCreating tray icon...")

image = Image.new('RGB', (64, 64), color=(255, 0, 0))
draw = ImageDraw.Draw(image)
draw.rectangle((8, 8, 56, 56), fill=(0, 255, 0))

def on_clicked(icon, item):
    print("Menu item clicked! Icon is working!")
    icon.stop()

menu = pystray.Menu(
    pystray.MenuItem("Click Me to Exit", on_clicked, default=True)
)

icon = pystray.Icon("test_icon", image, "TEST TRAY ICON", menu)

print("Starting icon.run() - look for a RED/GREEN square icon in the system tray!")
print("Right-click it and select 'Click Me to Exit' to stop this test.")
print("If you see NO icon, the test has FAILED.")

icon.run()

print("\nIcon stopped. Test complete.")
input("Press Enter to exit...")
