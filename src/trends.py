"""趋势分析模块：汇总多期日报，分析 AI 热点变化趋势"""

import os
import json
import re
from datetime import datetime, timedelta
from openai import OpenAI


TREND_PROMPT = """你是一位 AI 行业趋势分析师。你的任务是阅读过去 {days} 天（共 {count} 期）的 AI 日报关键词，然后产出一份结构清晰的趋势周报。

## 输出格式（纯文本，不要代码块包裹）

# AI 趋势周报 - {start} 至 {end}

## 📊 热点词频
列出本周出现频率最高的 5-8 个关键词，格式：
- **关键词** | 出现次数 | 简要解读：为什么这个词这周特别热

## 🔥 本周重大进展
3-5 条最重要的进展或变化，每条包含：
- **事件** | 影响分析

## 📈 趋势观察
2-3 条你观察到的中短期趋势，格式：
- **趋势** | 证据支持（引用具体关键词或事件）

## 🔮 下周关注
1-2 个值得重点跟踪的方向

## 分析原则
1. 基于数据说话，不要编造没有依据的结论
2. 区分"短期热点"和"长期趋势"
3. 中文输出，技术术语保留英文
"""


def analyze_keywords(days: int = 7) -> str:
    """读取 search_index 中的关键词数据，生成趋势分析"""
    index_path = "output/search_index.json"
    if not os.path.exists(index_path):
        return ""

    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)

    # 筛选时间范围内数据
    cutoff = datetime.now() - timedelta(days=days)
    recent = []
    for item in index:
        try:
            item_date = datetime.strptime(item["date"], "%Y-%m-%d")
            if item_date >= cutoff:
                recent.append(item)
        except ValueError:
            continue

    if len(recent) < 2:
        return ""

    recent.sort(key=lambda x: x["date"])
    start_date = recent[0]["date"]
    end_date = recent[-1]["date"]

    # 统计关键词频率
    word_freq = {}
    for item in recent:
        for kw in item.get("keywords", []):
            word = kw.strip().lower()
            if len(word) < 4:
                continue
            word_freq[word] = word_freq.get(word, 0) + 1

    # 取前 20 个高频词
    top_words = sorted(word_freq.items(), key=lambda x: -x[1])[:20]
    kw_summary = "\n".join([f"- {w} (出现 {c} 次)" for w, c in top_words])

    # 本期日报标题汇总
    titles = "\n".join([f"- {item.get('title', '')} ({item['date']})" for item in recent])

    user_prompt = f"""时间段：{start_date} 至 {end_date}
期数：{len(recent)} 期

各期标题：
{titles}

高频关键词（按频率排序）：
{kw_summary}

请基于以上数据生成趋势周报。"""

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY 未设置")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        max_tokens=4096,
        temperature=0.7,
        messages=[
            {"role": "system", "content": TREND_PROMPT.format(
                days=days, count=len(recent), start=start_date, end=end_date
            )},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content
