# -*- coding: UTF-8 -*-
"""
Uma Musume 自動育成主程式（auto-nurturing 版本）
使用方式：python src/auto_main.py
按 ESC 可隨時停止
"""
import json
import os
import sys
import time
import cv2
import numpy as np
import pyautogui
from pynput.keyboard import Key, Listener

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from scrshot import screenshot_from_window_name, record_title_bar_height
from template_matching import single_match_gray

# ── 全域停止旗標 ──────────────────────────────────────────────
_stop = False

def _on_press(key):
    global _stop
    if key == Key.esc:
        print("\n[INFO] 收到 ESC，即將停止...")
        _stop = True


# ── 連線錯誤偵測 ────────────────────────────────────────────────
# 模板1：舊版 VPN 斷線符號
_ERR_TEMPLATE_PATH = "./assets/image/matching_template/connection_error/s1.png"
_ERR_REGION = [111, 131, 0, 119]
_err_template = None

# 模板2：通信エラー 彈窗（白底文字「通信中にエラーが発生しました」）
_ERR2_TEMPLATE_PATH = "./assets/image/matching_template/connection_error/comm_error.png"
_ERR2_REGION = [346, 371, 25, 345]
_err2_template = None

def _load_error_template():
    global _err_template, _err2_template
    if os.path.exists(_ERR_TEMPLATE_PATH):
        _err_template = cv2.imread(_ERR_TEMPLATE_PATH)
    else:
        print(f"[WARN] 找不到連線錯誤模板：{_ERR_TEMPLATE_PATH}")
    if os.path.exists(_ERR2_TEMPLATE_PATH):
        _err2_template = cv2.imread(_ERR2_TEMPLATE_PATH)
    else:
        print(f"[WARN] 找不到通信エラー模板：{_ERR2_TEMPLATE_PATH}")

def _is_connection_error(screen):
    h, w = screen.shape[:2]
    if _err_template is not None:
        r = _ERR_REGION
        crop = screen[r[0]:min(r[1],h), r[2]:min(r[3],w)]
        if single_match_gray(crop, _err_template, 127, 0.01):
            return True
    if _err2_template is not None:
        r = _ERR2_REGION
        crop = screen[r[0]:min(r[1],h), r[2]:min(r[3],w)]
        if single_match_gray(crop, _err2_template, 127, 0.05):
            return True
    return False


# ── 場景載入 ────────────────────────────────────────────────────
def _load_scenes(path="./assets/scenes.json"):
    with open(path, encoding="utf-8") as f:
        lst = json.load(f)
    scene_map = {}
    for s in lst:
        template = cv2.imread(s["template"])
        if template is None:
            print(f"[ERROR] 找不到模板圖：{s['template']}")
            print("  → 請先執行 python tools/make_templates.py")
            sys.exit(1)
        s["_template"] = template
        scene_map[s["id"]] = s
    return scene_map


# ── 截圖 ────────────────────────────────────────────────────────
def _grab():
    """回傳 (screen_bgr, window_pos) 或 None"""
    result = screenshot_from_window_name()
    return result  # (img, (x, y)) or None


# ── 場景偵測 ────────────────────────────────────────────────────
def _detect(screen, scene, return_minval=False):
    r = scene["detect_region"]  # [y1, y2, x1, x2]
    h, w = screen.shape[:2]
    y1, y2, x1, x2 = r
    y2 = min(y2, h)
    x2 = min(x2, w)
    if y2 <= y1 or x2 <= x1:
        return (False, 1.0) if return_minval else False
    crop = screen[y1:y2, x1:x2]
    return single_match_gray(crop, scene["_template"],
                             scene["threshold"], scene["admitval"],
                             return_minval=return_minval)


# ── 點擊 ────────────────────────────────────────────────────────
def _click(window_pos, xy, delay=0.5):
    x, y = xy
    pyautogui.click(window_pos[0] + x, window_pos[1] + y)
    time.sleep(delay)


# ── 等待指定場景出現 ─────────────────────────────────────────────
def _wait_for_scene(scene, config, poll=None):
    """
    持續截圖直到 scene 偵測成功或超時。
    回傳 (screen, window_pos)，超時或中斷回傳 None。
    """
    timeout = scene.get("timeout", config["normal_timeout_sec"])
    if poll is None:
        poll = config["poll_interval_sec"]

    sid = scene["id"]
    start = time.time()

    while not _stop:
        elapsed = time.time() - start
        if elapsed > timeout:
            print(f"[ERROR] 場景 {sid} 等待超時（超過 {timeout:.0f} 秒）")
            return None

        result = _grab()
        if result is None:
            time.sleep(poll)
            continue

        screen, window_pos = result

        if _is_connection_error(screen):
            print("[ERROR] 偵測到連線錯誤（VPN 可能已斷線），程式終止")
            sys.exit(1)

        if _detect(screen, scene):
            return screen, window_pos

        time.sleep(poll)

    return None  # ESC pressed


# ── 處理分支：點擊後等哪個畫面出現 ─────────────────────────────
def _wait_for_branch(next_ids, scene_map, config, timeout=15):
    start = time.time()
    poll = config["poll_interval_sec"]
    while not _stop:
        if time.time() - start > timeout:
            print(f"[ERROR] 分支等待超時（候選：{next_ids}），程式終止")
            sys.exit(1)

        result = _grab()
        if result is None:
            time.sleep(poll)
            continue

        screen, window_pos = result

        if _is_connection_error(screen):
            print("[ERROR] 偵測到連線錯誤，程式終止")
            sys.exit(1)

        # 對每個候選都算分數，取「有通過自己 admitval 門檻」中分數最低（最像）的
        # 那一個，而不是照 next_ids 順序第一個通過就採用──避免某個候選的偵測區域
        # 剛好誤判命中時，因為排序在前而搶先於分數明顯更好的正確候選。
        best_nid = None
        best_val = None
        for nid in next_ids:
            passed, minval = _detect(screen, scene_map[nid], return_minval=True)
            if passed and (best_val is None or minval < best_val):
                best_nid = nid
                best_val = minval
        if best_nid is not None:
            return best_nid

        time.sleep(poll)

    return None


# ── auto_running 特殊處理：先確認進入自動，再長等結束 ───────────
def _handle_auto_running(scene, scene_map, config):
    """
    1. 先等 auto_running 畫面出現（確認自動育成已啟動）
    2. 再長等 end_01 出現（育成結束）
    回傳下一個 scene_id，或 None（停止/錯誤）
    """
    # 階段 1：嘗試確認自動育成啟動（偵測失敗不終止，繼續等完成）
    print("[INFO] 等待自動育成啟動畫面（おまかせ中...）...")
    res = _wait_for_scene(scene, config)
    if res is None:
        if _stop:
            return None
        print("[WARN] 未偵測到 auto_running 畫面（動畫背景多變），假設已啟動，繼續等待完成...")
    else:
        print("[INFO] 自動育成已確認啟動，等待育成結束中...")

    # 階段 2：長等 end_01
    end_scene = scene_map["end_01"]
    wait_timeout = scene.get("wait_end_timeout", config["auto_wait_timeout_sec"])
    wait_poll = scene.get("wait_end_poll", config["auto_poll_interval_sec"])
    start = time.time()

    while not _stop:
        elapsed = time.time() - start
        if elapsed > wait_timeout:
            print(f"[ERROR] 育成等待超時（超過 {wait_timeout:.0f} 秒），程式終止")
            sys.exit(1)

        mins = int(elapsed / 60)
        poll_desc = f"{int(wait_poll // 60)} 分鐘" if wait_poll >= 60 else f"{wait_poll:.0f} 秒"
        print(f"[INFO] 育成中...（已等待 {mins} 分鐘，每 {poll_desc}確認一次）")

        result = _grab()
        if result is None:
            print("[WARN] 視窗截圖失敗（視窗可能被干擾），5 秒後重試...")
            time.sleep(5)
            continue

        screen, window_pos = result
        if _is_connection_error(screen):
            print("[ERROR] 偵測到連線錯誤，程式終止")
            sys.exit(1)
        if _detect(screen, end_scene):
            print("[INFO] 偵測到育成結束！")
            return "end_01"

        time.sleep(wait_poll)

    return None


# ── 單次育成迴圈 ─────────────────────────────────────────────────
def run_once(scene_map, config, start_id="main_screen"):
    """執行一輪完整育成，從 start_id 回到 main_screen。"""
    current_id = start_id
    prev_id = None  # lag 回退用：記錄上一個成功偵測的場景

    while not _stop:
        scene = scene_map[current_id]
        print(f"[INFO] 等待場景：{current_id}（{scene['desc']}）")

        # auto_running 有特殊的兩階段等待
        if current_id == "auto_running":
            next_id = _handle_auto_running(scene, scene_map, config)
            if next_id is None:
                return False
            prev_id = current_id
            current_id = next_id
            continue

        # 一般場景：等待出現
        res = _wait_for_scene(scene, config)
        if res is None:
            if prev_id is not None and not _stop:
                print(f"[WARN] 場景 {current_id} 等待超時，嘗試偵測前一個場景 {prev_id}（防lag）...")
                res = _wait_for_scene(scene_map[prev_id], config)
                if res is None:
                    print(f"[ERROR] 前一個場景 {prev_id} 也未偵測到，程式終止")
                    return False
                print(f"[INFO] 偵測到前一個場景 {prev_id}，回退並重新繼續")
                scene = scene_map[prev_id]
                current_id = prev_id
                prev_id = None
            else:
                return False
        screen, window_pos = res

        # 點擊前等待：全域延遲 + 場景專屬延遲（動畫場景）
        pre_delay = config.get("pre_click_delay_sec", 0)
        wait_before = scene.get("wait_before_click_sec", 0)
        total_wait = pre_delay + wait_before
        if total_wait > 0:
            if wait_before > 0:
                print(f"[INFO] 等待 {total_wait:.1f} 秒後再點擊（過渡+動畫）")
            else:
                print(f"[INFO] 等待 {total_wait:.1f} 秒後再點擊（過渡）")
            time.sleep(total_wait)
            # 重新截圖取得最新 window_pos
            result2 = _grab()
            if result2:
                screen, window_pos = result2

        # 執行點擊
        click_xy = scene.get("click")
        if click_xy:
            print(f"[INFO] 點擊 ({click_xy[0]}, {click_xy[1]})")
            _click(window_pos, click_xy, config["click_delay_sec"])

        # 決定下一個場景
        next_val = scene["next"]

        if isinstance(next_val, list):
            # 分支：等兩個候選場景哪個先出現
            print(f"[INFO] 等待分支場景：{next_val}")
            next_id = _wait_for_branch(next_val, scene_map, config, timeout=20)
            if next_id is None:
                return False
            print(f"[INFO] 進入分支：{next_id}")
            prev_id = current_id
            current_id = next_id
        else:
            prev_id = current_id
            current_id = next_val

        # 完成一輪（回到主畫面）
        if current_id == "main_screen":
            return True

    return False


# ── 主程式 ──────────────────────────────────────────────────────
def main():
    global _stop

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="main_screen",
                        help="指定起始場景 ID（預設 main_screen）")
    args = parser.parse_args()

    listener = Listener(on_press=_on_press)
    listener.start()

    # 載入設定
    if not os.path.exists("./config.json"):
        print("[ERROR] 找不到 config.json")
        sys.exit(1)
    with open("./config.json", encoding="utf-8") as f:
        config = json.load(f)

    # 載入場景（同時驗證模板圖都存在）
    scene_map = _load_scenes()
    _load_error_template()

    if args.start not in scene_map:
        print(f"[ERROR] 找不到場景 ID：{args.start}")
        print(f"  可用：{list(scene_map.keys())}")
        sys.exit(1)

    # 調整視窗大小（寬度 + 高度）
    print("[INFO] 調整遊戲視窗大小...")
    record_title_bar_height()
    _grab()  # 強制觸發一次 MoveWindow 以修正高度

    loop_count = config.get("loop_count", -1)
    cycle = 0

    print("[INFO] 程式啟動，按 ESC 可隨時停止")
    if args.start != "main_screen":
        print(f"[INFO] 從場景 {args.start} 開始（單次補完模式）")
    else:
        print(f"[INFO] 循環次數設定：{'無限' if loop_count == -1 else loop_count} 次")

    while not _stop:
        if loop_count != -1 and cycle >= loop_count:
            print(f"[INFO] 已完成 {loop_count} 次育成，程式結束")
            break

        cycle += 1
        print(f"\n{'='*40}")
        print(f"[INFO] 開始第 {cycle} 次育成")
        print(f"{'='*40}")

        success = run_once(scene_map, config, start_id=args.start)
        # 第一輪之後回到正常流程
        args.start = "main_screen"

        if not success:
            if _stop:
                print("[INFO] 使用者停止程式")
            else:
                print("[ERROR] 育成流程中斷，程式終止")
            break

        print(f"[INFO] 第 {cycle} 次育成完成！")

    print("[INFO] 程式結束")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
