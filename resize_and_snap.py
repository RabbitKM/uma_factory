# -*- coding: UTF-8 -*-
import sys
import ctypes
import ctypes.wintypes
import win32gui
sys.path.insert(0, "./src")
from scrshot import screenshot_from_window_name, record_title_bar_height, get_current_size, enum_cb

def get_hwnd():
    winlist = []
    win32gui.EnumWindows(enum_cb, winlist)
    for proc in winlist:
        if proc[1] == "umamusume":
            return proc[0]
    return None

hwnd = get_hwnd()
if hwnd is None:
    print("找不到 umamusume 視窗，請確認遊戲已開啟")
    exit()

before = get_current_size(hwnd)
print(f"調整前：左={before[0]} 上={before[1]} 寬={before[2]-before[0]} 高={before[3]-before[1]}")

record_title_bar_height()
result = screenshot_from_window_name()

after = get_current_size(hwnd)
print(f"調整後：左={after[0]} 上={after[1]} 寬={after[2]-after[0]} 高={after[3]-after[1]}")

if result:
    import cv2
    cv2.imwrite("snap.png", result[0])
    h, w = result[0].shape[:2]
    print(f"截圖：{w} x {h} px，已存成 snap.png")
