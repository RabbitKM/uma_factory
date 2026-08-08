# -*- coding: UTF-8 -*-
"""
從標記好的 calibrate_out/tmp/<scene_id>.png 自動讀取座標。

使用方式：
  python tools/read_markers.py <scene_id>          # 只顯示座標
  python tools/read_markers.py <scene_id> apply    # 顯示並寫入 scenes.json

標記規則：
  藍色矩形外框（RGB 接近 0,0,255）→ detect_region
  紫色實心圓（R>100, B>100, G<80）→ click 座標
"""
import sys, os, json
import numpy as np
import cv2

os.chdir(os.path.join(os.path.dirname(__file__), '..'))

TMP_Y_OFFSET = 7
TITLE_BAR_PX = 40   # 跳過頂部標題列（Windows 按鈕避免誤抓）
SCENES_PATH = './assets/scenes.json'


def imread_unicode(path):
    buf = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def detect_blue_rect(img):
    """
    偵測使用者畫的藍色矩形框。
    回傳 (y_min, y_max, x_min, x_max) in tmp 座標，或 None。
    """
    b = img[:, :, 0].astype(int)
    g = img[:, :, 1].astype(int)
    r = img[:, :, 2].astype(int)

    mask = ((b > 160) & (b - r > 80) & (b - g > 80)).astype(np.uint8) * 255
    # 忽略標題列（Windows 關閉/最小化按鈕）
    mask[:TITLE_BAR_PX, :] = 0

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    best_span = 0
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < 10 or h < 5:
            continue
        span = w * h
        if span > best_span:
            best_span = span
            best = (y, y + h, x, x + w)

    return best


def detect_purple_circle(img):
    """
    偵測使用者畫的紫色實心圓重心。
    回傳 (cx, cy) in tmp 座標，或 None。
    """
    b = img[:, :, 0].astype(int)
    g = img[:, :, 1].astype(int)
    r = img[:, :, 2].astype(int)

    mask = (r > 100) & (b > 100) & (g < 80) & (np.abs(r - b) < 120)
    ys, xs = np.where(mask)
    if len(ys) < 5:
        return None
    return int(xs.mean()), int(ys.mean())


def main():
    if len(sys.argv) < 2:
        print("用法：python tools/read_markers.py <scene_id> [apply]")
        sys.exit(1)

    scene_id = sys.argv[1]
    do_apply = len(sys.argv) >= 3 and sys.argv[2] == 'apply'

    img_path = f'./calibrate_out/tmp/{scene_id}.png'
    if not os.path.exists(img_path):
        print(f"[ERROR] 找不到圖片：{img_path}")
        sys.exit(1)

    img = imread_unicode(img_path)
    if img is None:
        print(f"[ERROR] 無法讀取圖片：{img_path}")
        sys.exit(1)

    print(f"[INFO] 圖片尺寸：{img.shape[1]}x{img.shape[0]}")

    # 偵測藍框
    rect = detect_blue_rect(img)
    new_region = None
    if rect:
        ty1, ty2, tx1, tx2 = rect
        py1 = ty1 - TMP_Y_OFFSET
        py2 = ty2 - TMP_Y_OFFSET
        new_region = [py1, py2, tx1, tx2]
        print(f"[藍框] tmp 座標 y={ty1}~{ty2}, x={tx1}~{tx2}")
        print(f"       → detect_region = {new_region}")
    else:
        print("[藍框] 未偵測到藍色矩形")

    # 偵測紫圓
    circle = detect_purple_circle(img)
    new_click = None
    if circle:
        tcx, tcy = circle
        new_click = [tcx, tcy - TMP_Y_OFFSET]
        print(f"[紫圓] tmp 座標 ({tcx}, {tcy})")
        print(f"       → click = {new_click}")
    else:
        print("[紫圓] 未偵測到紫色圓形")

    if new_region is None and new_click is None:
        print("[WARN] 沒有偵測到任何標記，請確認顏色是否符合規則。")
        sys.exit(0)

    if not do_apply:
        print("\n（加上 apply 參數可直接寫入 scenes.json）")
        sys.exit(0)

    # 讀取並更新 scenes.json
    with open(SCENES_PATH, encoding='utf-8') as f:
        scenes = json.load(f)

    scene = next((s for s in scenes if s['id'] == scene_id), None)
    if scene is None:
        print(f"[ERROR] scenes.json 中找不到場景 {scene_id}")
        sys.exit(1)

    if new_region:
        scene['detect_region'] = new_region
    if new_click:
        scene['click'] = new_click

    with open(SCENES_PATH, 'w', encoding='utf-8') as f:
        json.dump(scenes, f, ensure_ascii=False, indent=2)

    print(f"[OK] scenes.json 已更新（{scene_id}）")


if __name__ == '__main__':
    main()
