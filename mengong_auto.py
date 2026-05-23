"""
孟恭的道路指引 — 全自動彙整腳本
版本：V1.0 | 2026-05-23

排程時間（台灣時間）：
    每週三 23:00 / 每週六 17:00

流程：
    1. 抓取 YouTube RSS（股癌頻道最新影片）
    2. 呼叫本機 Claude Code CLI 進行投資要點彙整
    3. 寫入 mengong_summary.json
    4. git commit + push 至 GitHub

執行方式（手動測試）：
    python mengong_auto.py
"""

import os
import json
import subprocess
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# ==========================================
# 設定區
# ==========================================
CHANNEL_ID  = "UC23rnlQU_qE3cec9x709peA"   # 股癌 Gooaye YouTube Channel ID
FETCH_COUNT = 8                              # 抓取最新幾支影片
OUTPUT_JSON = "mengong_summary.json"
TW_TZ       = timezone(timedelta(hours=8))
REPO_DIR    = os.path.dirname(os.path.abspath(__file__))

# ==========================================
# 1. 抓取 YouTube RSS
# ==========================================
def fetch_youtube_videos(channel_id: str, count: int) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    print(f"[1/4] 📡 抓取 YouTube RSS...")
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
    except Exception as e:
        print(f"      ❌ 失敗：{e}")
        return []

    ns = {
        "atom":  "http://www.w3.org/2005/Atom",
        "media": "http://search.yahoo.com/mrss/",
        "yt":    "http://www.youtube.com/xml/schemas/2015",
    }
    root   = ET.fromstring(res.content)
    videos = []

    for entry in root.findall("atom:entry", ns)[:count]:
        el_vid   = entry.find("yt:videoId",            ns)
        el_title = entry.find("atom:title",            ns)
        el_link  = entry.find("atom:link",             ns)
        el_pub   = entry.find("atom:published",        ns)
        el_desc  = entry.find(".//media:description",  ns)
        vid   = el_vid.text   if el_vid   is not None else ""
        title = el_title.text if el_title is not None else "(無標題)"
        link  = el_link.get("href", "") if el_link is not None else ""
        pub   = el_pub.text   if el_pub   is not None else ""
        desc  = (el_desc.text or "") if el_desc is not None else ""
        videos.append({
            "video_id":    vid,
            "title":       title,
            "link":        link,
            "pubDate":     pub,
            "thumbnail":   f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg" if vid else "",
            "description": desc[:300],
        })
        print(f"      ✅ {title[:50]}")

    print(f"      共取得 {len(videos)} 支影片")
    return videos


# ==========================================
# 2. 呼叫 Claude Code CLI 彙整
# ==========================================
def generate_summary_via_claude(videos: list[dict]) -> str:
    if not videos:
        return ""

    print(f"[2/4] 🤖 呼叫 Claude Code CLI 彙整...")

    context = "\n".join([
        f"{i+1}. 【{v['title']}】\n   {v['description'][:150]}"
        for i, v in enumerate(videos)
    ])

    prompt = (
        f"以下是股癌(Gooaye / 孟恭)最新 {len(videos)} 支 YouTube 影片清單：\n\n"
        f"{context}\n\n"
        "請以台股投資人視角，彙整出本週最重要的 4-6 個操作重點與市場觀點。\n"
        "格式要求：\n"
        "- 繁體中文\n"
        "- 條列式，每點以「・」開頭\n"
        "- 每點約 30-50 字，簡潔有力\n"
        f"- 最後加一行「📅 彙整基準：最新 {len(videos)} 支影片」"
    )

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            cwd=REPO_DIR,
        )
        if result.returncode != 0:
            err = result.stderr.strip()
            print(f"      ⚠️  Claude CLI 回傳錯誤：{err[:200]}")
            return f"⚠️ Claude CLI 錯誤：{err[:100]}"

        summary = result.stdout.strip()
        print(f"      ✅ 彙整完成（{len(summary)} 字元）")
        return summary

    except FileNotFoundError:
        msg = "找不到 claude 指令，請確認 Claude Code 已安裝並加入 PATH"
        print(f"      ❌ {msg}")
        return f"⚠️ {msg}"
    except subprocess.TimeoutExpired:
        msg = "Claude CLI 逾時（>120s）"
        print(f"      ❌ {msg}")
        return f"⚠️ {msg}"
    except Exception as e:
        print(f"      ❌ 未預期錯誤：{e}")
        return f"⚠️ 錯誤：{e}"


# ==========================================
# 3. 寫入 JSON
# ==========================================
def write_output(videos: list[dict], summary: str) -> None:
    print(f"[3/4] 💾 寫入 {OUTPUT_JSON}...")
    now_tw = datetime.now(TW_TZ)
    data = {
        "last_updated": now_tw.strftime("%Y-%m-%d %H:%M（自動排程）"),
        "channel_id":   CHANNEL_ID,
        "video_count":  len(videos),
        "summary":      summary,
        "videos":       videos,
    }
    out_path = os.path.join(REPO_DIR, OUTPUT_JSON)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"      ✅ 完成")


# ==========================================
# 4. Git commit + push
# ==========================================
def git_push() -> None:
    print(f"[4/4] 🚀 Git commit + push...")
    today = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M")
    try:
        subprocess.run(["git", "add", OUTPUT_JSON], cwd=REPO_DIR, check=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=REPO_DIR
        )
        if result.returncode == 0:
            print("      ℹ️  無變更，跳過 commit")
            return
        subprocess.run([
            "git", "commit", "-m",
            f"🤖 自動彙整：孟恭道路指引 {today}"
        ], cwd=REPO_DIR, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_DIR, check=True)
        print(f"      ✅ Push 完成")
    except subprocess.CalledProcessError as e:
        print(f"      ❌ Git 錯誤：{e}")


# ==========================================
# 主程式
# ==========================================
if __name__ == "__main__":
    print("=" * 55)
    print("🧭 孟恭的道路指引 — 全自動彙整排程")
    print(f"   執行時間：{datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 55)

    videos  = fetch_youtube_videos(CHANNEL_ID, FETCH_COUNT)
    summary = generate_summary_via_claude(videos)
    write_output(videos, summary)
    git_push()

    print("=" * 55)
    print("✅ 全部完成")
    print("=" * 55)
