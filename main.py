"""每日 AI 新闻邮件推送 · 入口。

运行语义：
- 定时模式（GitHub Actions 每小时触发）：仅当"本地时间点 == 配置 send_hour"才真正发送，
  否则静默跳过。这样发送时间完全由 config.yaml 控制，无需改 workflow。
- --force / 环境变量 FORCE=1（如 workflow_dispatch 手动触发）：忽略时间检查立即发送。
- --dry-run：只生成 preview.html，不发送（本地测试用，无需任何密钥/邮箱）。

用法：
  python main.py                 # 定时模式（到点才发）
  python main.py --force         # 立即发送
  python main.py --dry-run       # 仅生成预览 HTML
"""

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path

from config_loader import load_config
from mailer import send_email
from ranker import rank_and_select
from renderer import render
from sources import fetch_all
from summarizer import summarize

FORCE = os.getenv("FORCE") == "1"
LOCK_FILE = Path(".sent_lock")


def _today_str(offset_hours: int) -> str:
    return (datetime.utcnow() + timedelta(hours=offset_hours)).strftime("%Y-%m-%d")


def _already_sent(today: str) -> bool:
    if not LOCK_FILE.exists():
        return False
    return LOCK_FILE.read_text(encoding="utf-8").strip() == today


def _mark_sent(today: str):
    LOCK_FILE.write_text(today, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="每日 AI 新闻邮件推送")
    ap.add_argument("--dry-run", action="store_true", help="仅生成 preview.html，不发送")
    ap.add_argument("--force", action="store_true", help="忽略时间检查，立即发送")
    args = ap.parse_args()

    cfg = load_config()

    force = args.force or FORCE
    if not force and not args.dry_run:
        offset = cfg["schedule"]["timezone_offset"]
        local_hour = (datetime.utcnow().hour + offset) % 24
        send_hour = cfg["schedule"]["send_hour"]
        window = cfg["schedule"].get("send_window_hours", 1)
        allowed_hours = {(send_hour + i) % 24 for i in range(window)}

        if local_hour not in allowed_hours:
            print(f"本地时间 {local_hour:02d}:xx 不在发送窗口 "
                  f"[{send_hour:02d}:00–{(send_hour + window) % 24:02d}:00) 内，跳过。")
            return

        today = _today_str(offset)
        if _already_sent(today):
            print(f"今天 ({today}) 已经发送过，跳过，避免重复。")
            return

    print("【1/4】采集新闻中...")
    items = fetch_all(cfg)

    print("【2/4】按热度筛选排序...")
    selected = rank_and_select(items, cfg)
    print(f"  选出 {len(selected)} 条")

    print("【3/4】生成摘要/翻译...")
    summarize(selected, cfg["llm"])

    print("【4/4】渲染并发送...")
    html = render(selected, cfg)
    subject = f"AI 每日简报 · {datetime.now().strftime('%Y-%m-%d')}"

    if args.dry_run:
        with open("preview.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("  已生成 preview.html（未发送，可用于本地预览）")
        return

    send_email(html, subject, cfg["email"])
    if not args.dry_run:
        _mark_sent(_today_str(cfg["schedule"]["timezone_offset"]))
    print("完成 ✅ 邮件已发往", cfg["email"]["to"])


if __name__ == "__main__":
    main()
