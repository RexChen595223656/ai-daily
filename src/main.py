"""AI 日报生成器 - 主入口"""

import os
import sys
import argparse
from datetime import datetime

from dotenv import load_dotenv

from fetcher import fetch_all
from summarizer import generate_daily_report
from renderer import save_html, save_archive, update_archive, _read_archive


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
    args = parser.parse_args()

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

    # Step 2: 更新归档
    date_str = datetime.now().strftime("%Y-%m-%d")
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

    print(f"\n🎉 完成！")
    print(f"   https://rexchen595223656.github.io/ai-daily/")
    print(f"   https://rexchen595223656.github.io/ai-daily/archive.html")


if __name__ == "__main__":
    main()
