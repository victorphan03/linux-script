"""
Test script using Windows API directly (no pystray needed).
Run: python test_tray_win32.py
"""
import ctypes
import ctypes.wintypes
import threading
import time
import struct
import os

# Win32 constants
WM_USER = 0x0400
WM_TRAYICON = WM_USER + 1
WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205

NIF_ICON = 0x02
NIF_TIP = 0x04
NIF_MESSAGE = 0x01
NIM_ADD = 0x00
NIM_DELETE = 0x02

# Load DLLs
user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

# NOTIFYICONDATAW structure
class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("hWnd", ctypes.wintypes.HWND),
        ("uID", ctypes.wintypes.UINT),
        ("uFlags", ctypes.wintypes.UINT),
        ("uCallbackMessage", ctypes.wintypes.UINT),
        ("hIcon", ctypes.wintypes.HICON),
        ("szTip", ctypes.c_wchar * 128),
    ]

# WNDCLASSEXW
class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.UINT),
        ("style", ctypes.wintypes.UINT),
        ("lpfnWndProc", ctypes.CFUNCTYPE(ctypes.c_long, ctypes.wintypes.HWND, ctypes.wintypes.UINT, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM)),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.wintypes.HINSTANCE),
        ("hIcon", ctypes.wintypes.HICON),
        ("hCursor", ctypes.wintypes.HANDLE),
        ("hbrBackground", ctypes.wintypes.HANDLE),
        ("lpszMenuName", ctypes.wintypes.LPCWSTR),
        ("lpszClassName", ctypes.wintypes.LPCWSTR),
        ("hIconSm", ctypes.wintypes.HICON),
    ]

WNDPROC = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.wintypes.HWND, ctypes.wintypes.UINT, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM)

def wnd_proc(hwnd, msg, wparam, lparam):
    if msg == WM_TRAYICON:
        if lparam == WM_LBUTTONDBLCLK:
            print("Double-clicked on tray icon!")
        elif lparam == WM_RBUTTONUP:
            print("Right-clicked on tray icon! Exiting...")
            user32.PostMessageW(hwnd, WM_DESTROY, 0, 0)
    elif msg == WM_DESTROY:
        user32.PostQuitMessage(0)
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

print("=== Win32 Tray Icon Test ===")
print("Creating tray icon using raw Windows API...")

# Register window class
wnd_class = WNDCLASSEXW()
wnd_class.cbSize = ctypes.sizeof(WNDCLASSEXW)
wnd_class.lpfnWndProc = WNDPROC(wnd_proc)
wnd_class.hInstance = kernel32.GetModuleHandleW(None)
wnd_class.lpszClassName = "TestTrayWin32"

atom = user32.RegisterClassExW(ctypes.byref(wnd_class))
if not atom:
    print(f"FAILED to register window class! Error: {kernel32.GetLastError()}")
    input("Press Enter...")
    exit(1)

hInstance = kernel32.GetModuleHandleW(None)

# Create hidden window  
user32.CreateWindowExW.restype = ctypes.wintypes.HWND
user32.CreateWindowExW.argtypes = [
    ctypes.wintypes.DWORD, ctypes.wintypes.LPCWSTR, ctypes.wintypes.LPCWSTR, ctypes.wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.wintypes.HWND, ctypes.wintypes.HMENU, ctypes.wintypes.HINSTANCE, ctypes.c_void_p
]
hwnd = user32.CreateWindowExW(
    0, "TestTrayWin32", "Test Tray", 0,
    0, 0, 0, 0, None, None, hInstance, None
)
if not hwnd:
    print(f"FAILED to create window! Error: {kernel32.GetLastError()}")
    input("Press Enter...")
    exit(1)

# Use built-in Windows icon
hIcon = user32.LoadIconW(None, ctypes.cast(32516, ctypes.wintypes.LPCWSTR))  # IDI_SHIELD

# Add tray icon
nid = NOTIFYICONDATAW()
nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
nid.hWnd = hwnd
nid.uID = 1
nid.uFlags = NIF_ICON | NIF_TIP | NIF_MESSAGE
nid.uCallbackMessage = WM_TRAYICON
nid.hIcon = hIcon
nid.szTip = "TEST - Right click to exit"

result = shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
print(f"Shell_NotifyIconW result: {result} (1=success, 0=fail)")

if result:
    print("\nSUCCESS! Look for a SHIELD icon in the system tray.")
    print("RIGHT-CLICK the icon to exit this test.\n")
else:
    print(f"\nFAILED! Error: {kernel32.GetLastError()}")
    input("Press Enter...")
    exit(1)

# Message loop
msg = ctypes.wintypes.MSG()
while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
    user32.TranslateMessage(ctypes.byref(msg))
    user32.DispatchMessageW(ctypes.byref(msg))

# Cleanup
shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
print("Tray icon removed. Test complete.")
input("Press Enter to exit...")
