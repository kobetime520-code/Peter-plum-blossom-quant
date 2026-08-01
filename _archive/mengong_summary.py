"""
孟恭的道路指引 — 手動彙整腳本（本機規則式，無需任何 API）
版本：V2.0 | 2026-06-03

執行方式：
    python mengong_summary.py

環境變數需求：
    無（已移除 ANTHROPIC_API_KEY 依賴，改用本機規則式彙整）

輸出：
    mengong_summary.json（供 mengong.html 靜態讀取）

備註：
    彙整邏輯共用 mengong_auto.py 的 generate_summary_local()，
    與每日 21:00 自動排程完全一致。
"""

import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from mengong_auto import generate_summary_local

# ==========================================
# 設定區（僅需修改此處）
# ==========================================
CHANNEL_ID = "UC23rnlQU_qE3cec9x709peA"   # 股癌 Gooaye YouTube Channel ID
FETCH_COUNT = 8                            # 抓取最新幾支影片
OUTPUT_FILE = "mengong_summary.json"
TW_TZ = timezone(timedelta(hours=8))

# ==========================================
# 抓取 YouTube RSS
# ==========================================
def fetch_youtube_videos(channel_id: str, count: int) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    print(f"📡 抓取 YouTube RSS：{url}")
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
    except Exception as e:
        print(f"❌ YouTube RSS 抓取失敗：{e}")
        return []

    ns = {
        "atom":  "http://www.w3.org/2005/Atom",
        "media": "http://search.yahoo.com/mrss/",
        "yt":    "http://www.youtube.com/xml/schemas/2015",
    }
    root = ET.fromstring(res.content)
    videos = []

    for entry in root.findall("atom:entry", ns)[:count]:
        video_id_el = entry.find("yt:videoId", ns)
        title_el    = entry.find("atom:title", ns)
        link_el     = entry.find("atom:link", ns)
        pub_el      = entry.find("atom:published", ns)
        desc_el     = entry.find(".//media:description", ns)

        video_id    = video_id_el.text if video_id_el is not None else ""
        title       = title_el.text    if title_el    is not None else "(無標題)"
        link        = link_el.get("href", "") if link_el is not None else ""
        pub_date    = pub_el.text      if pub_el      is not None else ""
        description = (desc_el.text or "")[:300] if desc_el is not None else ""
        thumbnail   = f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg" if video_id else ""

        videos.append({
            "video_id":    video_id,
            "title":       title,
            "link":        link,
            "pubDate":     pub_date,
            "thumbnail":   thumbnail,
            "description": description,
        })
        print(f"   ✅ {title[:40]}")

    print(f"📺 共取得 {len(videos)} 支影片")
    return videos


# ==========================================
# 寫入 JSON
# ==========================================
def write_output(videos: list[dict], summary: str) -> None:
    now_tw = datetime.now(TW_TZ)
    data = {
        "last_updated": now_tw.strftime("%Y-%m-%d %H:%M"),
        "channel_id":   CHANNEL_ID,
        "video_count":  len(videos),
        "summary":      summary,
        "videos":       videos,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 已寫入 {OUTPUT_FILE}（{len(videos)} 支影片）")


# ==========================================
# 主程式
# ==========================================
if __name__ == "__main__":
    print("=" * 50)
    print("🧭 孟恭的道路指引 — 本機規則式彙整腳本（無需 API）")
    print(f"   執行時間：{datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    if CHANNEL_ID.startswith("UCxxx"):
        print("⚠️  請先在腳本頂部填入正確的 CHANNEL_ID")
        exit(1)

    videos  = fetch_youtube_videos(CHANNEL_ID, FETCH_COUNT)
    summary = generate_summary_local(videos)
    write_output(videos, summary)

    print("=" * 50)
    print("✅ 完成！請執行 git add mengong_summary.json && git push")
    print("=" * 50)
