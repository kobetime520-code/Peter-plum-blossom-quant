"""
孟恭的道路指引 — 全自動彙整腳本
版本：V2.0 | 2026-06-03

排程時間（台灣時間）：
    每天 21:00（晚上 9 點）

流程：
    1. 抓取 YouTube RSS（股癌頻道最新影片）— 公開來源，無需 API
    2. 本機規則式彙整投資要點 — 純關鍵字解析，零外部依賴、無需任何 API
    3. 寫入 mengong_summary.json
    4. git commit + push 至 GitHub

執行方式（手動測試）：
    python mengong_auto.py
"""

import os
import re
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
# 2. 本機規則式彙整（無需任何 API）
# ==========================================
# 主題規則：(顯示名稱, 關鍵字清單, 摘要句模板)
#   關鍵字比對範圍 = 影片標題 + 描述（全部轉小寫）
THEME_RULES = [
    ("台積電 / 權值股", ["台積電", "tsmc", "權值", "護國神山", "台股", "加權", "指數", "點"],
     "權值與大盤位階是本期觀察核心，留意指數高低點與台積電動向。"),
    ("AI 題材", ["ai", "agentic", "輝達", "nvidia", "算力", "晶片", "資料中心", "邊緣", "機器人"],
     "AI 相關族群仍是資金焦點，分辨基本面支撐強度，避免追逐純題材。"),
    ("風險控管", ["風險", "風控", "救命", "停損", "現金", "保本", "防禦", "減碼"],
     "孟恭反覆強調風險控管優先，高位階應提高現金水位、設好停損。"),
    ("高位 / 回調修正", ["回調", "修正", "壞掉", "高位", "過熱", "破", "跌", "捏破", "臨界"],
     "市場出現結構疑慮訊號，選股需避開弱勢股，等待回測再佈局。"),
    ("市場情緒 / 心態", ["信仰", "氣氛", "情緒", "心態", "測試", "躁動"],
     "短線方向受情緒主導，持股紀律受考驗，避免情緒性追高殺低。"),
    ("財報 / 基本面", ["財報", "季報", "財稅", "基本面", "獲利", "營收", "護城河", "節稅"],
     "財報與基本面是中長線護身符，留意具獲利與稅務優勢的標的。"),
    ("升降息 / 總經", ["升息", "降息", "聯準會", "fed", "通膨", "利率", "總經", "美元"],
     "總經與利率環境影響資金面，留意聯準會政策與匯率波動。"),
]


def _episode_label(title: str) -> str:
    """從標題擷取集數標籤，例：'EP666 | 🍐' -> 'EP666'。"""
    m = re.match(r"\s*(EP\s*\d+)", title, re.IGNORECASE)
    if m:
        return m.group(1).upper().replace(" ", "")
    return (title or "").split("|")[0].strip()[:8] or "本集"


def generate_summary_local(videos: list[dict]) -> str:
    """以本機關鍵字規則彙整投資要點，完全不呼叫任何 API。"""
    if not videos:
        return ""

    print(f"[2/4] 🧠 本機規則式彙整（無需 API）...")

    # 為每支影片建立可比對文字
    docs = []
    for v in videos:
        text = f"{v.get('title','')} {v.get('description','')}".lower()
        docs.append((_episode_label(v.get("title", "")), text))

    bullets = []

    # 最新動態（一定列出最新一集）
    latest = videos[0]
    latest_label = _episode_label(latest.get("title", ""))
    latest_desc = (latest.get("description", "") or "").strip().split("\n")[0][:40]
    if latest_desc:
        bullets.append(f"・**最新動態（{latest_label}）**：「{latest_desc}」— 為本期最新一集，優先掌握其當下市場定調。")
    else:
        bullets.append(f"・**最新動態**：最新一集為 {latest_label}，留意其當下市場定調。")

    # 主題比對：命中越多集的主題越優先
    theme_hits = []
    for name, keywords, sentence in THEME_RULES:
        eps = [label for label, text in docs if any(k in text for k in keywords)]
        if eps:
            theme_hits.append((len(eps), name, eps, sentence))

    theme_hits.sort(reverse=True, key=lambda x: x[0])

    # 取前 5 個主題，組成 4-6 點
    for _, name, eps, sentence in theme_hits[:5]:
        ep_str = "、".join(dict.fromkeys(eps))  # 去重保序
        bullets.append(f"・**{name}**：{sentence}（出現於 {ep_str}）")

    # 若主題命中過少，補一條通則提醒，確保至少 4 點
    if len(bullets) < 4:
        bullets.append("・**操作通則**：高位階以風險控管為先，嚴守停損紀律，不重倉單一題材。")

    bullets.append(f"📅 彙整基準：最新 {len(videos)} 支影片（本機自動產生，無需 API）")

    summary = "\n".join(bullets)
    print(f"      ✅ 彙整完成（{len(summary)} 字元，{len(bullets)-1} 個要點）")
    return summary


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
    summary = generate_summary_local(videos)
    write_output(videos, summary)
    git_push()

    print("=" * 55)
    print("✅ 全部完成")
    print("=" * 55)
