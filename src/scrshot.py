# -*- coding: UTF-8 -*-
import win32gui
import win32con
import time
from PIL import ImageGrab
import ctypes
import ctypes.wintypes
import numpy
import cv2
import pywintypes
import json
import pyautogui

def get_current_size(hwnd):
    try:
        f = ctypes.windll.dwmapi.DwmGetWindowAttribute
    except WindowsError:
        f = None
    if f:
        rect = ctypes.wintypes.RECT()
        DWMWA_EXTENDED_FRAME_BOUNDS = 9
        f(ctypes.wintypes.HWND(hwnd),
          ctypes.wintypes.DWORD(DWMWA_EXTENDED_FRAME_BOUNDS),
          ctypes.byref(rect),
          ctypes.sizeof(rect)
          )
        size = (rect.right - rect.left, rect.bottom - rect.top)
        return (rect.left, rect.top, rect.right, rect.bottom)

def enum_cb(hwnd, lst):
    lst.append((hwnd, win32gui.GetWindowText(hwnd)))

def kill_from_window_name(name):
    winlist = []
    win32gui.EnumWindows(enum_cb, winlist)
    for proc in winlist:
        if (name in proc[1]):
            screenshot_from_window_name(proc[1])
            time.sleep(5)
            pyautogui.hotkey("alt", "f4")

def screenshot_from_window_name(name="umamusume", scale="normal", pos=None, seg=None):
    fin = open("./assets/window_info.json", "r")
    title_bar_height = json.load(fin)["title_bar_height"]
    fin.close()
    winlist = []
    win32gui.EnumWindows(enum_cb, winlist)

    process = None
    for proc in winlist:
        if (proc[1]==name):
            process = proc[0]

    try:
        if (win32gui.GetWindowPlacement(process)[1]==2):
            win32gui.ShowWindow(process, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(process)
    except pywintypes.error:
        win32gui.ShowWindow(process, win32con.SW_MINIMIZE)
        time.sleep(1)
        win32gui.ShowWindow(process, win32con.SW_RESTORE)
        try:
            win32gui.SetForegroundWindow(process)
        except pywintypes.error:
            pass
        time.sleep(1)

    bbox = get_current_size(process)

    wait = False
    if ((scale=="normal" and bbox[2]-bbox[0]!=370) or (scale=="large" and bbox[2]-bbox[0]!=1082) or (scale=="very_large" and bbox[2]-bbox[0]!=2164)):
        wait = True

    window_height_map = {"normal": 686-30+title_bar_height, "large": 1862-30+title_bar_height, "very_large": 3724-30+title_bar_height}
    padded_border_width = bbox[0]-win32gui.GetWindowRect(process)[0]
    try:
        if (scale=="normal"):
            if (pos==None):
                win32gui.MoveWindow(process, bbox[0]-padded_border_width, bbox[1], 370+2*padded_border_width, window_height_map["normal"]+padded_border_width, True)
            else:
                win32gui.MoveWindow(process, pos[0]-padded_border_width, pos[1]-(title_bar_height-30), 370+2*padded_border_width, window_height_map["normal"]+padded_border_width, True)
        elif (scale=="large"):
            if (pos==None):
                win32gui.MoveWindow(process, bbox[0]-padded_border_width, bbox[1], 1082+2*padded_border_width, window_height_map["large"]+padded_border_width, True)
            else:
                win32gui.MoveWindow(process, pos[0]-padded_border_width, pos[1]-(title_bar_height-30), 1082+2*padded_border_width, window_height_map["large"]+padded_border_width, True)
        elif (scale=="very_large"):
            if (pos==None):
                win32gui.MoveWindow(process, bbox[0]-padded_border_width, bbox[1], 2164+2*padded_border_width, window_height_map["very_large"]+padded_border_width, True)
            else:
                win32gui.MoveWindow(process, pos[0]-padded_border_width, pos[1]-(title_bar_height-30), 2164+2*padded_border_width, window_height_map["very_large"]+padded_border_width, True)
    except pywintypes.error:
        return None

    if (wait==True):
        time.sleep(0.75)

    size_wait_deadline = time.time() + 15
    while True:
        if time.time() > size_wait_deadline:
            return None
        bbox = get_current_size(process)
        if (bbox[2]-bbox[0]!=370 and bbox[2]-bbox[0]!=1082 and bbox[2]-bbox[0]!=2164):
            time.sleep(0.1)
            continue
        else:
            coordinate = (bbox[0], bbox[1]+(title_bar_height-30))
            if (seg!=None):
                bbox = (bbox[0]+seg[2], bbox[1]+seg[0]+(title_bar_height-30), bbox[0]+seg[3], bbox[1]+seg[1]+(title_bar_height-30))
            else:
                bbox = (bbox[0], bbox[1]+(title_bar_height-30), bbox[2], bbox[3])
            break

    img = ImageGrab.grab(bbox)
    img = numpy.array(img)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return (img, (coordinate[0], coordinate[1]))

def restore_uma_window():
    winlist = []
    win32gui.EnumWindows(enum_cb, winlist)
    process = None
    for proc in winlist:
        if (proc[1]=="umamusume"):
            process = proc[0]
    bbox = get_current_size(process)
    padded_border_width = bbox[0]-win32gui.GetWindowRect(process)[0]
    win32gui.ShowWindow(process, win32con.SW_MINIMIZE)
    time.sleep(1)
    win32gui.ShowWindow(process, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(process)
    time.sleep(1)
    win32gui.MoveWindow(process, -padded_border_width, 0, 370+2*padded_border_width, 686+padded_border_width, True)

def record_title_bar_height():
    fout = open("./assets/window_info.json", "w")

    winlist = []
    win32gui.EnumWindows(enum_cb, winlist)

    process = None
    for proc in winlist:
        if (proc[1]=="umamusume"):
            process = proc[0]

    try:
        if (win32gui.GetWindowPlacement(process)[1]==2):
            win32gui.ShowWindow(process, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(process)
    except pywintypes.error:
        win32gui.ShowWindow(process, win32con.SW_MINIMIZE)
        time.sleep(1)
        win32gui.ShowWindow(process, win32con.SW_RESTORE)
        try:
            win32gui.SetForegroundWindow(process)
        except pywintypes.error:
            pass
        time.sleep(1)

    bbox = get_current_size(process)
    while (bbox[2]-bbox[0]!=370):
        try:
            if (win32gui.GetWindowPlacement(process)[1]==2):
                win32gui.ShowWindow(process, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(process)
        except pywintypes.error:
            win32gui.ShowWindow(process, win32con.SW_MINIMIZE)
            time.sleep(1)
            win32gui.ShowWindow(process, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(process)
            time.sleep(1)
        bbox = get_current_size(process)
        padded_border_width = bbox[0]-win32gui.GetWindowRect(process)[0]
        win32gui.MoveWindow(process, bbox[0]-padded_border_width, bbox[1], 370+2*padded_border_width, (bbox[3]-bbox[1])+padded_border_width, True)

    bbox = get_current_size(process)
    title_bar_height = (bbox[3]-bbox[1]) - (win32gui.GetClientRect(process)[3]-win32gui.GetClientRect(process)[1]) - 2
    json.dump({"title_bar_height": title_bar_height}, fout)
    fout.close()



if __name__ == "__main__":
    record_title_bar_height()