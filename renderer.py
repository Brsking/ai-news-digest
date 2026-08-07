"""HTML 邮件渲染（响应式、邮件客户端友好，内联样式）。"""

from datetime import datetime
from html import escape

from models import NewsItem

_SECTION_TITLE = {
    "global": "🔥 全球热度榜（按社区关注度排序）",
    "cn": "📰 中文精选",
    "en": "🌐 英文精选（附中文翻译）",
}


def _card(it: NewsItem) -> str:
    rank = f'<span class="rank">{it.rank}</span>'
    title_html = f'<a class="title" href="{escape(it.url)}">{escape(it.title)}</a>'
    # 英文条目：展示中文翻译标题
    trans_html = ""
    if it.is_english and it.translation and "未配置" not in it.translation and "失败" not in it.translation:
        trans_html = f'<div class="trans">译：{escape(it.translation)}</div>'
    meta = f'<div class="meta">{escape(it.source)}'
    if it.extra:
        meta += f' · {escape(it.extra)}'
    if it.published:
        meta += f' · {escape(it.published)}'
    meta += "</div>"
    summary = ""
    if it.summary:
        summary = f'<div class="summary">{escape(it.summary)}</div>'
    return f'<div class="card">{rank}{title_html}{trans_html}{meta}{summary}</div>'


def render(items: list, cfg: dict) -> str:
    today = datetime.now().strftime("%Y 年 %m 月 %d 日")
    sections_html = ""
    for sec in ("global", "cn", "en"):
        sub = [it for it in items if it.section == sec]
        if not sub:
            continue
        cards = "".join(_card(it) for it in sub)
        sections_html += (
            f'<h2 class="sec">{_SECTION_TITLE[sec]}</h2>{cards}'
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body>
<div class="wrap">
  <div class="header">
    <div class="h-title">AI 每日简报</div>
    <div class="h-sub">{today} · 按真实社区关注度筛选，非随机抓取</div>
  </div>
  {sections_html}
  <div class="footer">
    由 GitHub Actions 自动生成 · 配置驱动 · 热度信号来自 Hacker News / Reddit / GitHub
  </div>
</div>
<style>
  body {{ background:#f4f5f7; margin:0; padding:16px; font-family:-apple-system,"PingFang SC","Microsoft YaHei",Segoe UI,sans-serif; color:#1f2329; }}
  .wrap {{ max-width:680px; margin:0 auto; background:#fff; border-radius:14px; overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,.06); }}
  .header {{ background:linear-gradient(135deg,#2b6cff,#7b3bff); color:#fff; padding:22px 24px; }}
  .h-title {{ font-size:22px; font-weight:700; }}
  .h-sub {{ font-size:13px; opacity:.9; margin-top:6px; }}
  .sec {{ font-size:16px; margin:22px 24px 10px; padding-left:10px; border-left:4px solid #2b6cff; }}
  .card {{ margin:10px 24px; padding:14px 16px; background:#fafbfc; border:1px solid #eef0f3; border-radius:10px; position:relative; }}
  .rank {{ position:absolute; top:12px; right:14px; font-size:12px; color:#9aa0a6; font-weight:700; }}
  .title {{ font-size:15px; font-weight:600; color:#1a1a1a; text-decoration:none; line-height:1.45; }}
  .title:hover {{ color:#2b6cff; }}
  .trans {{ font-size:13px; color:#2b6cff; margin-top:6px; }}
  .meta {{ font-size:12px; color:#8a9099; margin-top:8px; }}
  .summary {{ font-size:13px; color:#3c4043; margin-top:8px; line-height:1.6; }}
  .footer {{ font-size:12px; color:#9aa0a6; text-align:center; padding:20px; border-top:1px solid #f0f1f3; margin-top:10px; }}
</style>
</body></html>"""
