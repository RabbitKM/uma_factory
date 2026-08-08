# -*- coding: UTF-8 -*-
"""
從 tmp/ 參考截圖自動裁切模板圖，存到 assets/auto_templates/
執行方式：python tools/make_templates.py
"""
import json
import os
import sys
import numpy as np
from PIL import Image

# tmp 截圖是 370x693，程式截圖是 370x686，頂部差 7px
SRC_Y_OFFSET = 7  # detect_region 是程式座標，換算到 tmp 截圖要加 7

TMP_DIR = "c:/Rabbit/_claude_projects/04_uma_factory_fix/tmp"
SCENES_PATH = "./assets/scenes.json"
DEBUG_DIR = "./assets/auto_templates/debug"


def load_image(path):
    """使用 PIL 讀圖（支援中文路徑），回傳 numpy BGR array"""
    pil = Image.open(path).convert("RGB")
    arr = np.array(pil)
    # RGB -> BGR for OpenCV compatibility
    return arr[:, :, ::-1].copy()


def save_image(arr, path):
    """儲存 BGR numpy array 為 PNG"""
    import cv2
    cv2.imwrite(path, arr)


def crop_region(img, region, y_offset=0):
    """
    region: [y1, y2, x1, x2]（程式截圖座標）
    y_offset: 如果來源圖片有 y 偏移（tmp +7），在此加入
    """
    y1, y2, x1, x2 = region
    y1 += y_offset
    y2 += y_offset
    h, w = img.shape[:2]
    y1 = max(0, y1)
    y2 = min(h, y2)
    x1 = max(0, x1)
    x2 = min(w, x2)
    return img[y1:y2, x1:x2]


def main():
    with open(SCENES_PATH, encoding="utf-8") as f:
        scenes = json.load(f)

    os.makedirs(DEBUG_DIR, exist_ok=True)

    ok_count = 0
    fail_count = 0

    for scene in scenes:
        sid = scene["id"]
        src_name = scene.get("src_screenshot")
        detect_region = scene["detect_region"]
        template_path = scene["template"]

        if not src_name:
            print(f"[SKIP] {sid}: 沒有 src_screenshot")
            continue

        src_path = os.path.join(TMP_DIR, src_name)
        if not os.path.exists(src_path):
            print(f"[FAIL] {sid}: 找不到 {src_path}")
            fail_count += 1
            continue

        img = load_image(src_path)
        h, w = img.shape[:2]

        # 裁切時加上 y_offset（tmp 比程式截圖多 7px 在頂部）
        crop = crop_region(img, detect_region, y_offset=SRC_Y_OFFSET)

        if crop.size == 0:
            print(f"[FAIL] {sid}: 裁切結果為空，region={detect_region}")
            fail_count += 1
            continue

        # 存模板
        os.makedirs(os.path.dirname(template_path), exist_ok=True)
        save_image(crop, template_path)

        # 存 debug 圖（原圖標記裁切區域）
        try:
            import cv2
            debug_img = img.copy()
            y1, y2, x1, x2 = detect_region
            y1s, y2s = y1 + SRC_Y_OFFSET, y2 + SRC_Y_OFFSET
            cv2.rectangle(debug_img, (x1, y1s), (x2, y2s), (0, 0, 255), 2)
            debug_path = os.path.join(DEBUG_DIR, f"{sid}.png")
            save_image(debug_img, debug_path)
        except Exception:
            pass

        ch, cw = crop.shape[:2]
        print(f"[OK]   {sid}: {template_path} ({cw}x{ch}px)")
        ok_count += 1

    print(f"\n完成：成功 {ok_count} 個，失敗 {fail_count} 個")
    if fail_count > 0:
        print("請確認 tmp/ 資料夾內的截圖名稱是否正確")
    if ok_count > 0:
        print(f"Debug 圖已存到 {DEBUG_DIR}/（紅框=偵測區域，請確認是否正確）")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
