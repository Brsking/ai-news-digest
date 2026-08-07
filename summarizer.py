"""LLM 摘要 / 翻译层。

职责（严格限定）：只做"把新闻变成中文可读摘要"，**绝不评判热度**——
热度由 ranker 用客观信号决定，避免主观偏差（计划书第 6 节避坑点）。

行为：
- 配置了 LLM key：批量调用 OpenAI 兼容接口，为每条生成 zh_title（中文标题）
  与 zh_summary（中文摘要）。英文条目用 translation 存中文标题，summary 存中文摘要；
  中文条目只精炼 summary。
- 无 key：降级——中文用标题/描述，英文标注"未配置 LLM，暂仅原文"，保证流程不中断。
"""

import json

from models import NewsItem

_BATCH = 8  # 每批处理的条目数，避免单次 prompt 过大


def _build_prompt(batch: list) -> str:
    lines = []
    for idx, it in enumerate(batch, 1):
        lang = "EN" if it.is_english else "CN"
        lines.append(f"{idx}. [{lang}] 标题: {it.title}\n   描述: {it.hint}")
    return (
        "你是一名中文科技新闻编辑。以下是若干 AI 新闻条目，部分为英文。\n"
        "请为每条生成：zh_title（中文标题）、zh_summary（中文摘要，1-2 句，提炼核心信息）。\n"
        "英文条目必须翻译成中文标题与摘要；中文条目可直接精炼，不要硬翻。\n"
        "只输出 JSON，格式严格为："
        '{"items":[{"id":序号,"zh_title":"...","zh_summary":"..."}]}\n\n'
        + "\n".join(lines)
    )


def _apply_result(batch: list, data: dict):
    for d in data.get("items", []):
        i = d.get("id")
        if not isinstance(i, int) or not (1 <= i <= len(batch)):
            continue
        it: NewsItem = batch[i - 1]
        zh_title = (d.get("zh_title") or "").strip()
        zh_summary = (d.get("zh_summary") or "").strip()
        if it.is_english:
            it.translation = zh_title           # 英文条目的中文标题（"单独的翻译版本"）
        it.summary = zh_summary or (it.hint or it.title)


def summarize(items: list, llm: dict):
    has_key = bool(llm.get("enabled")) and bool(llm.get("api_key"))

    if not has_key:
        print("  [LLM] 未配置 key，降级为原文/标题（仍会发送，只是无摘要翻译）")
        for it in items:
            it.summary = it.summary or it.hint or it.title
            if it.is_english:
                it.translation = "（未配置 LLM，暂仅原文）"
        return

    from openai import OpenAI
    client = OpenAI(api_key=llm["api_key"], base_url=llm["base_url"])

    for start in range(0, len(items), _BATCH):
        batch = items[start:start + _BATCH]
        try:
            resp = client.chat.completions.create(
                model=llm["model"],
                messages=[{"role": "user", "content": _build_prompt(batch)}],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            content = resp.choices[0].message.content or "{}"
            _apply_result(batch, json.loads(content))
        except Exception as e:
            print("  [LLM] 批次失败:", e)
            for it in batch:
                it.summary = it.summary or it.hint or it.title
                if it.is_english and not it.translation:
                    it.translation = "（翻译失败，暂仅原文）"
