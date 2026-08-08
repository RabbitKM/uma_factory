# -*- coding: UTF-8 -*-
"""
座標校準工具：在圖上畫出 scenes.json 裡每個場景的偵測區域和點擊位置

模式 1：從遊戲視窗即時截圖
  python tools/calibrate.py <scene_id>
  python tools/calibrate.py all

模式 2：從 tmp/ 參考截圖（不需要開遊戲）
  python tools/calibrate.py tmp <scene_id>
  python tools/calibrate.py tmp all

圖例：綠框 = 偵測區域，紅圓 = 點擊位置
輸出：calibrate_out/<scene_id>.png 或 calibrate_out/tmp/<scene_id>.png
"""
import sys, os, json, cv2
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

def imread_unicode(path):
    """支援中文路徑的 cv2.imread 替代"""
    buf = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)

def imwrite_unicode(path, img):
    """支援中文路徑的 cv2.imwrite 替代"""
    _, buf = cv2.imencode('.png', img)
    buf.tofile(path)

# tmp 截圖的 y 偏移（tmp 圖高 693，程式截圖 686，差 7px）
TMP_Y_OFFSET = 7

def draw_markers(img, click_xy, detect_region, color_click=(0,0,255), color_region=(0,255,0)):
    out = img.copy()
    r = detect_region
    cv2.rectangle(out, (r[2], r[0]), (r[3], r[1]), color_region, 2)
    if click_xy:
        cx, cy = click_xy
        cv2.circle(out, (cx, cy), 15, color_click, 2)
        cv2.line(out, (cx-20, cy), (cx+20, cy), color_click, 2)
        cv2.line(out, (cx, cy-20), (cx, cy+20), color_click, 2)
    return out

def run_live(scenes, target):
    from scrshot import screenshot_from_window_name, record_title_bar_height
    record_title_bar_height()
    result = screenshot_from_window_name()
    if result is None:
        print('找不到遊戲視窗')
        return
    screen, _ = result
    os.makedirs('./calibrate_out', exist_ok=True)

    targets = list(scenes.values()) if target == 'all' else [scenes[target]]
    for scene in targets:
        marked = draw_markers(screen, scene.get('click'), scene['detect_region'])
        out_path = f"./calibrate_out/{scene['id']}.png"
        imwrite_unicode(out_path, marked)
        print(f"  {scene['id']}: {out_path}")
    print('\n圖例：紅圓=點擊位置，綠框=場景偵測區域')

def run_tmp(scenes, target):
    os.makedirs('./calibrate_out/tmp', exist_ok=True)
    targets = list(scenes.values()) if target == 'all' else [scenes[target]]

    for scene in targets:
        src_name = scene.get('src_screenshot')
        if not src_name:
            print(f"  [SKIP] {scene['id']}：沒有 src_screenshot 欄位")
            continue

        img_path = f"../tmp/{src_name}"
        img = imread_unicode(img_path)
        if img is None:
            print(f"  [SKIP] {scene['id']}：找不到 {img_path}")
            continue

        # tmp 圖比程式截圖多 TMP_Y_OFFSET px，標記時補回
        r = scene['detect_region']
        r_tmp = [r[0]+TMP_Y_OFFSET, r[1]+TMP_Y_OFFSET, r[2], r[3]]

        click_xy = scene.get('click')
        click_tmp = None
        if click_xy:
            click_tmp = [click_xy[0], click_xy[1]+TMP_Y_OFFSET]

        marked = draw_markers(img, click_tmp, r_tmp)
        out_path = f"./calibrate_out/tmp/{scene['id']}.png"
        imwrite_unicode(out_path, marked)
        print(f"  {scene['id']}: {out_path}")

    print('\n圖例：紅圓=點擊位置，綠框=場景偵測區域（已補 +7px y 偏移）')

def main():
    with open('./assets/scenes.json', encoding='utf-8') as f:
        scenes = {s['id']: s for s in json.load(f)}

    args = sys.argv[1:]

    if args and args[0] == 'tmp':
        target = args[1] if len(args) > 1 else 'all'
        if target != 'all' and target not in scenes:
            print(f'找不到場景 {target}，可用：{list(scenes.keys())}')
            return
        run_tmp(scenes, target)
    else:
        target = args[0] if args else 'main_screen'
        if target != 'all' and target not in scenes:
            print(f'找不到場景 {target}，可用：{list(scenes.keys())}')
            return
        run_live(scenes, target)

if __name__ == '__main__':
    main()
