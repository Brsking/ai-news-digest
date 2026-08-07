"""热度排序与去重 —— 本项目的核心差异化。

设计要点：
- HN / Reddit / GitHub 带客观热度信号（score / stars），按 hot_score 降序取 Top。
- RSS 无热度信号（hot_score=0），不参与热度竞争，但用"配额"保底，
  保证每天都有中文精选 + 英文精选覆盖，避免全是英文社区热帖。
- 按 URL 规范化去重，避免同新闻多源重复发。
"""

from models import NewsItem


def _norm_url(url: str) -> str:
    u = (url or "").strip().lower()
    u = u.split("?")[0].split("#")[0]
    if u.endswith("/"):
        u = u[:-1]
    return u


def rank_and_select(items: list, cfg: dict) -> list:
    top_n = cfg["digest"]["top_n"]
    rss_quota = cfg["digest"].get("rss_quota", 6)

    scored = [it for it in items if it.hot_score > 0]
    rss = [it for it in items if it.hot_score == 0]

    # 1) 有热度信号的源：按分数降序
    scored.sort(key=lambda x: x.hot_score, reverse=True)
    selected = scored[: max(0, top_n - rss_quota)]

    # 2) RSS 配额保底：按发布日期倒序（越新越优先）
    rss.sort(key=lambda x: x.published, reverse=True)
    selected += rss[:rss_quota]

    # 3) URL 去重（同链接只留一条，优先保留已选中的靠前的）
    seen = set()
    out: list = []
    for it in selected:
        key = _norm_url(it.url)
        if key in seen:
            continue
        seen.add(key)
        out.append(it)

    # 4) 填排名
    for i, it in enumerate(out, 1):
        it.rank = i

    return out
