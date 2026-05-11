"""AI 摘要模块：调用 DeepSeek API 将原始数据转为结构化日报"""

import os
from typing import Dict, List
from openai import OpenAI


SYSTEM_PROMPT = """你是一位专业的 AI 领域日报编辑。你的任务是阅读今天收集的 AI 相关资讯（论文、开源项目、社区讨论），然后产出一份结构清晰、有洞察力的日报。

## 输出格式要求
使用以下结构输出纯文本（不要用 Markdown 代码块包裹）：

# AI 日报 - {日期}

## 📌 今日要点
用 3-5 点概括今天最重要的 AI 动态，每点一句话，突出"为什么重要"而不是简单复述标题。

## 📄 论文精读
列出值得关注的论文，每篇格式：
- **论文标题** | 要点：一句话概括核心贡献 | [arXiv](URL)

## ⭐ 热门开源
列出值得关注的开源项目，每个格式：
- **项目名** | 要点：一句话概括做了什么 | Stars: ⭐数量 | [GitHub](URL)

## 💬 社区热议
列出 HackerNews 等技术社区的优质讨论，每个格式：
- **标题** | 要点：讨论焦点或亮点 | [Hacker News](URL)

## 🤖 编辑点评
一段简短的编辑点评（100 字以内）：今天的趋势是什么？有什么值得深入跟进的方向？

## 编辑原则
1. 质量优先：不是所有的信息都值得放进日报，筛选真正有价值的
2. 有洞察：不只翻译标题，要说出"为什么这个值得关注"
3. 简洁：每条信息一句话要点即可
4. 中文输出，技术术语保留英文
"""


def build_user_prompt(data: Dict[str, List[Dict]]) -> str:
    """将抓取的结构化数据组装成给 LLM 的 Prompt"""
    sections = []
    sections.append(f"日期：{data.get('date', 'unknown')}")

    papers = data.get("arxiv_papers", [])
    if papers:
        sections.append("\n## 最新论文")
        for p in papers:
            authors = ", ".join(p.get("authors", []))
            sections.append(
                f"- 标题: {p['title']}\n"
                f"  作者: {authors}\n"
                f"  摘要: {p['summary'][:300]}\n"
                f"  链接: {p['url']}"
            )
    else:
        sections.append("\n## 最新论文\n今日无新论文数据。")

    repos = data.get("github_trending", [])
    if repos:
        sections.append("\n## 热门开源项目")
        for r in repos:
            today = f" 🔥今日+{r['today_stars']}" if r.get('today_stars', 0) > 0 else ""
            sections.append(
                f"- {r['name']}: {r['description'][:200]} "
                f"(语言: {r.get('language', 'N/A')}, ⭐{r.get('stars', 0)}{today}) "
                f"{r['url']}"
            )
    else:
        sections.append("\n## 热门开源项目\n今日无热门仓库数据。")

    stories = data.get("hackernews", [])
    if stories:
        sections.append("\n## 社区热议")
        for s in stories:
            sections.append(f"- {s['title']} (👍{s.get('score', 0)}) {s['url']}")
    else:
        sections.append("\n## 社区热议\n今日无 HN 热帖数据。")

    return "\n".join(sections)


def generate_daily_report(data: Dict[str, List[Dict]],
                          model: str = "deepseek-chat") -> str:
    """调用 DeepSeek 生成日报"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY 未设置，请在 .env 文件中配置")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    user_prompt = build_user_prompt(data)

    response = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    from fetcher import fetch_all

    raw = fetch_all()
    report = generate_daily_report(raw)
    print(report)
