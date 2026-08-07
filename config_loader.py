"""配置加载：config.yaml + 环境变量覆盖。

设计原则：
- 普通配置（时间点、邮箱、源开关）走 config.yaml，可提交进仓库。
- 密钥（LLM key、Resend key、SMTP 密码）只从环境变量读取，绝不写进文件。
"""

import os
import yaml


# 默认配置：用户 config.yaml 会合并覆盖这里
DEFAULTS = {
    "schedule": {
        "timezone_offset": 8,   # Asia/Shanghai = UTC+8
        "send_hour": 8,         # 每天本地 8 点发送
        "send_minute": 0,
    },
    "email": {
        "to": "",                       # 你的收件邮箱（必填）
        "from_name": "AI 每日简报",
        "provider": "resend",           # resend | smtp
        "resend_api_key": "",           # 优先读环境变量 RESEND_API_KEY
        "resend_from": "ai-news@yourdomain.com",  # 改成你的域名邮箱
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "",                # 读 SMTP_USER 环境变量
        "smtp_pass": "",                # 读 SMTP_PASS 环境变量
    },
    "llm": {
        "enabled": True,
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "",                  # 优先读环境变量 DEEPSEEK_API_KEY
        "model": "deepseek-chat",
        # 想换 OpenAI / 通义 / 混元：改 base_url + api_key + model 即可
    },
    "sources": {
        "hn": {"enabled": True, "count": 30, "mode": "best"},   # top | best
        "reddit": {"enabled": True,
                    "subreddits": ["MachineLearning", "artificial", "singularity"],
                    "count": 20},
        "github": {"enabled": True, "count": 15, "min_stars": 15,
                   "days": 2},          # 近 N 天新仓库，按 stars 排序
        "rss_cn": {"enabled": True, "max_per": 8, "feeds": [
            {"name": "机器之心", "url": "https://www.jiqizhixin.com/rss"},
            {"name": "36氪", "url": "https://36kr.com/feed"},
            {"name": "量子位", "url": "https://www.qbitai.com/feed"},
        ]},
        "rss_en": {"enabled": True, "max_per": 8, "feeds": [
            {"name": "TechCrunch AI",
             "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
            {"name": "MIT Tech Review AI",
             "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed"},
        ]},
    },
    "digest": {
        "top_n": 14,        # 最终发送条数
        "rss_quota": 6,     # 其中至少保留多少条 RSS（保证中英文精选覆盖）
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并两个 dict，override 优先。"""
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str = "config.yaml") -> dict:
    user_cfg = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}

    cfg = _deep_merge(DEFAULTS, user_cfg)

    # 密钥只从环境变量覆盖（环境变量优先于 config 里的空值）
    cfg["llm"]["api_key"] = os.getenv("DEEPSEEK_API_KEY") or cfg["llm"].get("api_key", "")
    cfg["email"]["resend_api_key"] = os.getenv("RESEND_API_KEY") or cfg["email"].get("resend_api_key", "")
    cfg["email"]["smtp_user"] = os.getenv("SMTP_USER") or cfg["email"].get("smtp_user", "")
    cfg["email"]["smtp_pass"] = os.getenv("SMTP_PASS") or cfg["email"].get("smtp_pass", "")
    # GitHub Actions 自带 GITHUB_TOKEN，可用于提高 GitHub 搜索额度
    cfg["github_token"] = os.getenv("GITHUB_TOKEN", "")

    return cfg
