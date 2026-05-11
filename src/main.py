"""AI 日报生成器 - 主入口

使用方法：
    python src/main.py                     # 生成今日日报
    python src/main.py --no-ai             # 仅抓取数据，不调用 AI（调试用）
    python src/main.py --arxiv 5 --hn 15   # 自定义抓取数量
"""

import os
import sys
import argparse
from datetime import datetime

from dotenv import load_dotenv

from fetcher import fetch_all
from summarizer import generate_daily_report
from renderer import save_html


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="AI 日报生成器")
    parser.add_argument("--arxiv", type=int, default=8, help="arXiv 论文数量")
    parser.add_argument("--hn", type=int, default=30, help="Hacker News 抓取数量")
    parser.add_argument("--ph", type=int, default=5, help="Product Hunt 产品数量")
    parser.add_argument("--hf", type=int, default=5, help="Hugging Face 论文数量")
    parser.add_argument("--no-ai", action="store_true", help="仅抓取数据，不调用 AI")
    parser.add_argument("--model", default="deepseek-chat", help="LLM 模型名称")
    parser.add_argument("--output", type=str, help="输出文件路径（默认 output/daily-<日期>.html）")
    args = parser.parse_args()

    # Step 1: 抓取数据
    print("🔍 正在抓取数据源...")
    raw_data = fetch_all(max_arxiv=args.arxiv, max_hn=args.hn,
                         max_ph=args.ph, max_hf=args.hf)
    arxiv_count = len(raw_data["arxiv_papers"])
    github_count = len(raw_data["github_trending"])
    hn_count = len(raw_data["hackernews"])
    ph_count = len(raw_data["tech_news"])
    hf_count = len(raw_data["huggingface"])
    print(f"   arXiv: {arxiv_count} 篇论文")
    print(f"   GitHub: {github_count} 个热门仓库")
    print(f"   HN:     {hn_count} 条热帖")
    print(f"   News:   {ph_count} 条科技新闻")
    print(f"   HF:     {hf_count} 篇论文")

    if args.no_ai:
        # 调试模式：直接输出原始数据汇总
        from renderer import render
        md_lines = ["# AI 日报（调试模式）\n", f"日期：{raw_data['date']}\n"]
        if raw_data["arxiv_papers"]:
            md_lines.append("\n## 论文\n")
            for p in raw_data["arxiv_papers"]:
                md_lines.append(f"- **{p['title']}** | {p['url']}")
        if raw_data["github_trending"]:
            md_lines.append("\n## 开源\n")
            for r in raw_data["github_trending"]:
                md_lines.append(f"- **{r['name']}** ⭐{r['stars']} | {r['url']}")
        if raw_data["hackernews"]:
            md_lines.append("\n## HN\n")
            for s in raw_data["hackernews"]:
                md_lines.append(f"- {s['title']} | {s['url']}")
        md_content = "\n".join(md_lines)
    else:
        # Step 2: AI 生成日报
        print("🤖 正在调用 DeepSeek 生成日报...")
        try:
            md_content = generate_daily_report(raw_data, model=args.model)
        except ValueError as e:
            print(f"❌ {e}")
            sys.exit(1)

    # Step 3: 生成 HTML
    print("📄 正在生成 HTML 页面...")
    date_str = datetime.now().strftime("%Y-%m-%d")
    output = args.output or f"output/daily-{date_str}.html"
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    path = save_html(md_content, output_path=output)

    # GitHub Pages: index.html 指向最新日报
    index_path = "output/index.html"
    save_html(md_content, output_path=index_path)

    print(f"\n🎉 完成！在浏览器打开查看:")
    print(f"   file://{os.path.abspath(path)}")
    print(f"   file://{os.path.abspath(index_path)} (index)")


if __name__ == "__main__":
    main()
