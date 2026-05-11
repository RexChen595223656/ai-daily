"""AI 摘要模块：调用 DeepSeek API 将原始数据转为结构化日报"""

import os
from typing import Dict, List
from openai import OpenAI


SYSTEM_PROMPT = """你是一位资深的 AI 领域主编，在科技媒体领域有 10 年以上经验，擅长从大量碎片信息中提炼核心趋势。你的日报被 AI 从业者视为每日必读。

## 核心工作流
1. 扫读所有原始素材（论文、开源项目、HN 讨论、科技新闻）
2. 识别今天的核心主题 —— 哪些信息之间存在关联？有什么隐藏趋势？
3. 按以下结构输出，确保每一条都有洞察，而非信息堆砌

## 输出结构（纯文本，不要代码块包裹）

# AI 日报 - {日期}

## 📌 今日趋势
写 4-5 条趋势观察，每条包含：「现象」+「为什么重要」。不要简单复述标题，要提炼背后的意义。
格式：**一句话趋势** | 背后的原因或影响

选材范围覆盖所有数据源，但同一来源不要超过 2 条。
*示例：*
- **多智能体安全研究加速** | 今天有 3 篇独立论文从不同角度诊断多 Agent 系统的隐藏行为，说明社区正从"如何让 Agent 协作"转向"如何控制协作风险"

## 📄 论文精读
从上万篇论文中选出今天最值得读的 3-5 篇，每篇格式：
- **论文标题** | 一句话说明核心贡献，以及"为什么这篇值得花时间读" | [arXiv](URL)

筛选标准：novelty（创新性）> relevance（相关性）> recency（时效性）

## ⭐ 热门开源
精选 3-5 个值得关注的开源项目，每个格式：
- **项目名** | 一句话说明解决了什么问题 + 值得关注的原因 | Stars: ⭐数量 | [GitHub](URL)

优先选 AI infra / 开发工具 / 应用类项目，排除纯娱乐或与 AI 无关的项目。

## 🛠 科技新闻
TechCrunch / ArsTechnica 等媒体的 AI 相关新闻，2-3 条：
- **标题** | 一句话新闻要点 + 对行业的潜在影响 | [链接](URL)

## 💬 社区热议
HackerNews 上最有价值的讨论，2-3 条：
- **标题** (👍点赞数) | 讨论的核心观点或争议点 | [Hacker News](URL)

## 🤖 主编点评
一段 150 字以内的深度点评（不是总结上文），内容包括：
- 今天的最大信号是什么（多数人可能忽略的）
- 本周值得跟进的方向
- 如果有跨 section 的关联（某论文作者在 HN 讨论、某开源项目解决了某新闻中提到的问题），在此点出

## 编辑准则
1. **有洞察 > 有信息**：读者读日报不是为了看信息列表，是为了理解"这跟我有什么关系"
2. **筛选是最高价值**：宁可只写 3 条精挑细选的，也不要写 10 条凑数的
3. **不说正确的废话**：避免"值得关注""值得期待"这类空洞表述
4. **交叉关联优先**：当两个数据源指向同一趋势时（如某论文在 HN 被讨论），这是最值得写进日报的内容
5. **中文输出，核心术语保留英文**（如 Agent、RAG、Inference 等）
"""


def build_user_prompt(data: Dict[str, List[Dict]]) -> str:
    """将抓取的结构化数据组装成给 LLM 的 Prompt"""
    sections = []
    sections.append(f"日期：{data.get('date', 'unknown')}")

    papers = data.get("arxiv_papers", [])
    if papers:
        sections.append("\n## arXiv 最新论文")
        for p in papers:
            authors = ", ".join(p.get("authors", []))
            sections.append(
                f"- 标题: {p['title']}\n"
                f"  作者: {authors}\n"
                f"  摘要: {p['summary'][:300]}\n"
                f"  链接: {p['url']}"
            )

    repos = data.get("github_trending", [])
    if repos:
        sections.append("\n## GitHub Trending")
        for r in repos:
            today = f" 🔥今日+{r['today_stars']}" if r.get('today_stars', 0) > 0 else ""
            sections.append(
                f"- {r['name']}: {r['description'][:200]} "
                f"(语言: {r.get('language', 'N/A')}, ⭐{r.get('stars', 0)}{today}) "
                f"{r['url']}"
            )

    stories = data.get("hackernews", [])
    if stories:
        sections.append("\n## HackerNews")
        for s in stories:
            sections.append(f"- {s['title']} (👍{s.get('score', 0)}) {s['url']}")

    tech = data.get("tech_news", [])
    if tech:
        sections.append("\n## 科技新闻")
        for t in tech:
            sections.append(f"- {t['title']}: {t.get('description', '')[:200]} {t['url']}")

    hf_papers = data.get("huggingface", [])
    if hf_papers:
        sections.append("\n## Hugging Face")
        for h in hf_papers:
            sections.append(f"- {h['title']}: {h.get('description', '')[:200]} {h['url']}")

    info = [
        f"总素材量：{len(papers)} 篇论文 + {len(repos)} 个开源项目 + {len(stories)} 条 HN 讨论 + {len(tech)} 条科技新闻 + {len(hf_papers)} 篇 HF 论文",
    ]
    sections.append("\n---\n" + "\n".join(info))
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
        temperature=0.7,
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
