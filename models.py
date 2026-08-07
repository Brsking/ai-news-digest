"""统一新闻条目模型。

所有采集源（HN / Reddit / GitHub / RSS）最终都转成 NewsItem，
后续的排序、摘要、渲染都只认这一个结构，互不耦合。
"""

from dataclasses import dataclass


@dataclass
class NewsItem:
    title: str           # 标题（英文源为英文原文）
    url: str             # 跳转链接
    source: str          # 来源名，如 "Hacker News" / "Reddit r/artificial" / "机器之心"
    section: str = "global"   # 展示分区：global(国际热度) / cn(中文精选) / en(英文精选·翻译)
    raw_score: int = 0   # 原始热度（HN/Reddit 的 points、GitHub 的 stars）
    hot_score: float = 0.0   # 用于排序的热度分（RSS 无信号则=0，靠配额保底）
    published: str = ""  # 发布日期 YYYY-MM-DD
    is_english: bool = True
    summary: str = ""    # 中文摘要（LLM 生成；无 key 时退化为标题/描述）
    translation: str = ""  # 英文条目的中文标题翻译（"单独的翻译版本"）
    hint: str = ""       # 原始描述 / 副标题（喂给 LLM 做摘要）
    extra: str = ""      # 展示用附加信息，如 "1,234 points" / "320 ★" / "88 评论"
    rank: int = 0        # 最终排名（渲染时填）
