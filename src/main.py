"""AI 日报生成器 - 主入口"""

import os
import sys
import json
import re
import argparse
from datetime import datetime

from dotenv import load_dotenv

from fetcher import fetch_all
from summarizer import generate_daily_report
from renderer import save_html, save_archive, save_rss, save_trend_report, update_archive, _read_archive
from notifier import push
from trends import analyze_keywords


def _update_search_index(date_str: str, md_content: str):
    """更新搜索索引"""
    index_path = "output/search_index.json"
    index = []
    if os.path.exists(index_path):
        try:
            with open(index_path, "r") as f:
                index = json.load(f)
        except Exception:
            pass

    lines = md_content.split("\n")
    keywords = []
    for line in lines:
        bold = re.findall(r'\*\*(.+?)\*\*', line)
        keywords.extend(bold)
        if line.startswith("- **"):
            title = line.split("**")[1] if "**" in line else ""
            if title:
                keywords.append(title)

    title = "AI 日报"
    for line in lines:
        if line.startswith("# AI 日报"):
            title = line.replace("# ", "").strip()
            break

    # 提取摘要：今日趋势部分的前 500 字符
    summary = title
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- **") and len(stripped) > 20:
            summary = stripped[2:].replace("**", "").strip()[:300]
            break

    entry = {
        "date": date_str,
        "title": title,
        "summary": summary,
        "keywords": list(set(k for k in keywords if len(k) > 2))[:50]
    }
    index = [e for e in index if e["date"] != date_str]
    index.append(entry)
    index.sort(key=lambda x: x["date"], reverse=True)
    os.makedirs("output", exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="AI 日报生成器")
    parser.add_argument("--arxiv", type=int, default=8, help="arXiv 论文数量")
    parser.add_argument("--hn", type=int, default=30, help="Hacker News 抓取数量")
    parser.add_argument("--ph", type=int, default=5, help="科技新闻数量")
    parser.add_argument("--hf", type=int, default=5, help="Hugging Face 论文数量")
    parser.add_argument("--no-ai", action="store_true", help="仅抓取数据，不调用 AI")
    parser.add_argument("--model", default="deepseek-chat", help="LLM 模型名称")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--trend", type=int, default=0,
                        help="生成趋势报告，指定天数（7=周报，30=月报）")
    args = parser.parse_args()

    # 趋势模式：不抓取数据，直接从历史分析
    if args.trend > 0:
        print(f"📊 正在生成 {args.trend} 天趋势报告...")
        try:
            trend_md = analyze_keywords(days=args.trend)
            if not trend_md:
                print("⚠️ 数据不足，至少需要 2 期日报才能生成趋势")
                return
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - __import__("datetime").timedelta(days=args.trend)).strftime("%Y-%m-%d")
            from renderer import save_trend_report
            save_trend_report(trend_md, start_date, end_date, args.trend)
            print(f"✅ 趋势报告完成")
        except ValueError as e:
            print(f"❌ {e}")
        return

    # Step 1: 抓取数据
    print("🔍 正在抓取数据源...")
    raw_data = fetch_all(max_arxiv=args.arxiv, max_hn=args.hn,
                         max_ph=args.ph, max_hf=args.hf)
    print(f"   arXiv: {len(raw_data['arxiv_papers'])} 篇论文")
    print(f"   GitHub: {len(raw_data['github_trending'])} 个热门仓库")
    print(f"   HN:     {len(raw_data['hackernews'])} 条热帖")
    print(f"   News:   {len(raw_data['tech_news'])} 条科技新闻")
    print(f"   HF:     {len(raw_data['huggingface'])} 篇论文")

    if args.no_ai:
        from renderer import render_daily
        md_lines = ["# AI 日报（调试模式）\n", f"日期：{raw_data['date']}\n"]
        for key, label in [("arxiv_papers", "论文"), ("github_trending", "开源"),
                           ("hackernews", "HN"), ("tech_news", "科技新闻"),
                           ("huggingface", "HF")]:
            items = raw_data.get(key, [])
            if items:
                md_lines.append(f"\n## {label}\n")
                for item in items:
                    md_lines.append(f"- **{item.get('title', '')}** | {item.get('url', '')}")
        md_content = "\n".join(md_lines)
    else:
        print("🤖 正在调用 DeepSeek 生成日报...")
        try:
            md_content = generate_daily_report(raw_data, model=args.model)
        except ValueError as e:
            print(f"❌ {e}")
            sys.exit(1)

    # Step 2: 更新搜索索引 + 归档
    date_str = datetime.now().strftime("%Y-%m-%d")
    _update_search_index(date_str, md_content)
    all_dates = update_archive(date_str)

    # 找出前一日期和后一日期用于导航
    try:
        idx = all_dates.index(date_str)
        prev_date = all_dates[idx + 1] if idx + 1 < len(all_dates) else ""
        next_date = all_dates[idx - 1] if idx - 1 >= 0 else ""
    except ValueError:
        prev_date = next_date = ""

    # Step 3: 生成 HTML
    print("📄 正在生成 HTML 页面...")
    os.makedirs("output", exist_ok=True)

    # 日报页面
    daily_path = args.output or f"output/daily-{date_str}.html"
    save_html(md_content, daily_path, date=date_str,
              prev_date=prev_date, next_date=next_date)

    # index.html 指向最新一期
    save_html(md_content, "output/index.html", date=date_str,
              prev_date=prev_date, next_date=next_date)

    # 归档页
    save_archive(all_dates)

    # RSS 订阅
    try:
        with open("output/search_index.json", "r") as f:
            rss_items = json.load(f)
        save_rss(rss_items)
    except Exception as e:
        print(f"⚠️ RSS 生成跳过: {e}")

    # Step 4: 推送
    page_url = f"https://rexchen595223656.github.io/ai-daily/daily-{date_str}.html"
    push(md_content, page_url)

    print(f"\n🎉 完成！")
    print(f"   https://rexchen595223656.github.io/ai-daily/")
    print(f"   https://rexchen595223656.github.io/ai-daily/archive.html")
    if os.getenv("PUSH_CHANNEL"):
        print(f"   📲 已推送至 {os.getenv('PUSH_CHANNEL')}")


if __name__ == "__main__":
    main()
