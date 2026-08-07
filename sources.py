"""多源采集层。

每个采集函数返回 List[NewsItem]，互不影响；fetch_all 用线程池并行抓取，
任一源失败只跳过该源，不影响其他源（健壮性要求）。
"""

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import feedparser
import requests

from models import NewsItem

_HEADERS = {"User-Agent": "ai-news-digest/1.0 (https://github.com)"}

# AI 相关关键词，用于 HN 这种"全站"源做粗筛
_AI_KEYWORDS = [
    "ai", "a.i", "llm", "gpt", "chatgpt", "openai", "anthropic", "claude",
    "gemini", "machine learning", "deep learning", "neural", "transformer",
    "diffusion", "llama", "mistral", "deepseek", "qwen", "agent", " rag",
    "fine-tun", "reinforcement learning", "nlp", "computer vision",
]


def _is_ai_related(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in _AI_KEYWORDS)


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


# ---------------- Hacker News（Firebase API，免费无 key）----------------

def fetch_hn(count: int = 30, mode: str = "best") -> list:
    items = []
    try:
        base = "https://hacker-news.firebaseio.com/v0"
        ids = requests.get(f"{base}/{mode}stories.json", timeout=15).json()[:count]
        for sid in ids:
            it = requests.get(f"{base}/item/{sid}.json", timeout=15).json()
            if not it or not it.get("title"):
                continue
            title = it["title"]
            if not _is_ai_related(title):
                continue
            ts = it.get("time", 0)
            items.append(NewsItem(
                title=title,
                url=it.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                source="Hacker News", section="global",
                raw_score=it.get("score", 0), hot_score=float(it.get("score", 0)),
                published=datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d") if ts else "",
                is_english=True,
                hint=it.get("text", "") or "",
                extra=f"{it.get('score', 0)} points · {it.get('descendants', 0)} 评论",
            ))
    except Exception as e:
        print("  [HN] 采集失败:", e)
    return items


# ---------------- Reddit（hot 排序，免费，需 UA）----------------

def fetch_reddit(subreddits: list, count: int = 20) -> list:
    items = []
    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit={count}"
            r = requests.get(url, headers=_HEADERS, timeout=15)
            if r.status_code != 200:
                print(f"  [Reddit r/{sub}] 返回 {r.status_code}，跳过")
                continue
            for c in r.json().get("data", {}).get("children", []):
                p = c["data"]
                items.append(NewsItem(
                    title=p["title"],
                    url=f"https://www.reddit.com{p['permalink']}",
                    source=f"Reddit r/{sub}", section="global",
                    raw_score=p.get("score", 0), hot_score=float(p.get("score", 0)),
                    published=datetime.utcfromtimestamp(p.get("created_utc", 0)).strftime("%Y-%m-%d"),
                    is_english=True,
                    hint=p.get("selftext", "")[:500] or "",
                    extra=f"{p.get('score', 0)} points · {p.get('num_comments', 0)} 评论",
                ))
        except Exception as e:
            print(f"  [Reddit r/{sub}] 采集失败:", e)
    return items


# ---------------- GitHub Trending（近 N 天新仓库，按 stars）----------------

def fetch_github(count: int = 15, min_stars: int = 15, days: int = 2,
                 token: str = "") -> list:
    items = []
    try:
        since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        q = f"ai OR llm OR machine-learning created:>{since}"
        url = "https://api.github.com/search/repositories"
        params = {"q": q, "sort": "stars", "order": "desc", "per_page": count}
        headers = {"Accept": "application/vnd.github+json", "User-Agent": _HEADERS["User-Agent"]}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code != 200:
            print(f"  [GitHub] 返回 {r.status_code}，跳过（可能因额度限制，建议配置 GITHUB_TOKEN）")
            return items
        for repo in r.json().get("items", []):
            stars = repo.get("stargazers_count", 0)
            if stars < min_stars:
                continue
            items.append(NewsItem(
                title=repo["name"],
                url=repo["html_url"],
                source="GitHub Trending", section="global",
                raw_score=stars, hot_score=float(stars),
                published=repo.get("created_at", "")[:10],
                is_english=True,
                hint=repo.get("description") or "",
                extra=f"{stars} ★",
            ))
    except Exception as e:
        print("  [GitHub] 采集失败:", e)
    return items


# ---------------- RSS（中英各若干，无热度信号，靠配额保底）----------------

def _fetch_rss_one(feed: dict, max_per: int, section: str) -> list:
    out = []
    try:
        d = feedparser.parse(feed["url"])
        if d.bozo and not d.entries:
            print(f"  [RSS {feed['name']}] 解析异常，跳过")
            return out
        for e in d.entries[:max_per]:
            title = e.get("title", "").strip()
            link = e.get("link", "")
            if not title or not link:
                continue
            pub = ""
            if e.get("published_parsed"):
                pub = datetime(*e["published_parsed"][:6]).strftime("%Y-%m-%d")
            elif e.get("published"):
                pub = e["published"][:10]
            summary = ""
            if e.get("summary"):
                summary = re.sub("<[^>]+>", "", e["summary"])[:400]
            out.append(NewsItem(
                title=title, url=link, source=feed["name"], section=section,
                raw_score=0, hot_score=0.0,
                published=pub, is_english=_has_cjk(title) is False,
                hint=summary,
                extra="",
            ))
    except Exception as err:
        print(f"  [RSS {feed['name']}] 采集失败:", err)
    return out


def fetch_rss_cn(feeds: list, max_per: int = 8) -> list:
    out = []
    for f in feeds:
        out += _fetch_rss_one(f, max_per, section="cn")
    return out


def fetch_rss_en(feeds: list, max_per: int = 8) -> list:
    out = []
    for f in feeds:
        out += _fetch_rss_one(f, max_per, section="en")
    return out


# ---------------- 并行汇聚 ----------------

def fetch_all(cfg: dict) -> list:
    """并行抓取所有启用的源，失败源自动跳过。"""
    s = cfg["sources"]
    jobs = []  # (name, callable)

    if s["hn"].get("enabled"):
        jobs.append(("HN", lambda: fetch_hn(**{k: s["hn"][k] for k in ("count", "mode")})))
    if s["reddit"].get("enabled"):
        jobs.append(("Reddit", lambda: fetch_reddit(
            s["reddit"]["subreddits"], s["reddit"]["count"])))
    if s["github"].get("enabled"):
        jobs.append(("GitHub", lambda: fetch_github(
            s["github"]["count"], s["github"]["min_stars"],
            s["github"]["days"], cfg.get("github_token", ""))))
    if s["rss_cn"].get("enabled"):
        jobs.append(("RSS_CN", lambda: fetch_rss_cn(
            s["rss_cn"]["feeds"], s["rss_cn"]["max_per"])))
    if s["rss_en"].get("enabled"):
        jobs.append(("RSS_EN", lambda: fetch_rss_en(
            s["rss_en"]["feeds"], s["rss_en"]["max_per"])))

    results: list = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(fn): name for name, fn in jobs}
        for fut in futures:
            name = futures[fut]
            try:
                results += fut.result()
                print(f"  [OK] {name}")
            except Exception as e:
                print(f"  [FAIL] {name}: {e}")

    print(f"  采集合计 {len(results)} 条")
    return results
