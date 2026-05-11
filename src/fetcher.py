"""数据抓取模块：从多个信息源获取 AI 相关的最新内容"""

import re
import feedparser
import requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from typing import List, Dict


ARXIV_API_URL = "https://export.arxiv.org/api/query"
GITHUB_TRENDING_URL = "https://github.com/trending"
HN_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

HEADERS = {
    "User-Agent": "AI-Daily-Bot/1.0 (AI Product Manager Portfolio Project)"
}


def fetch_arxiv(max_results: int = 10) -> List[Dict]:
    """从 arXiv 获取最新 AI/机器学习论文（抓取 New Submissions 页面）"""
    papers = []
    categories = ["cs.AI", "cs.CL", "cs.LG"]
    collected = 0

    for cat in categories:
        if collected >= max_results:
            break
        url = f"https://arxiv.org/list/{cat}/new"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
        except requests.RequestException:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        dl = soup.find("dl")
        if not dl:
            continue

        dds = dl.find_all("dd")
        dts = dl.find_all("dt")

        for dt, dd in zip(dts, dds):
            if collected >= max_results:
                break

            # 提取 arXiv ID 和链接
            link_tag = dt.find("a", title="Abstract")
            if not link_tag:
                continue
            paper_id = link_tag.get("href", "").split("/")[-1].split("v")[0]
            arxiv_url = f"https://arxiv.org/abs/{paper_id}"

            # 标题
            title_div = dd.find("div", class_="list-title")
            title = title_div.text.replace("Title:", "").strip() if title_div else ""

            # 作者
            authors_div = dd.find("div", class_="list-authors")
            authors = []
            if authors_div:
                for a_tag in authors_div.find_all("a"):
                    authors.append(a_tag.text.strip())

            # 摘要（arXiv 页面摘要默认折叠，用 API 获取）
            summary = ""

            # 分类
            cats_div = dd.find("div", class_="list-subjects")
            cats = []
            if cats_div:
                cats_text = cats_div.text.replace("Subjects:", "").strip()
                cats = [c.strip() for c in cats_text.split(";")]

            papers.append({
                "title": title,
                "url": arxiv_url,
                "summary": summary,
                "authors": authors[:5],
                "categories": cats,
                "published": "",
                "source": f"arxiv_{cat}"
            })
            collected += 1

    # 对获取到的论文补充摘要（arXiv API 按 ID 查询更稳定）
    if papers:
        ids = [p["url"].split("/abs/")[1] for p in papers]
        _enrich_abstracts(ids, papers)

    return papers


def _enrich_abstracts(ids: List[str], papers: List[Dict]):
    """通过 arXiv API 批量获取摘要"""
    id_list = ",".join(ids)
    url = f"https://export.arxiv.org/api/query?id_list={id_list}&max_results={len(ids)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        for i, entry in enumerate(feed.entries):
            if i < len(papers):
                summary = entry.get("summary", "")
                papers[i]["summary"] = re.sub(r"\s+", " ", summary).strip()[:500]
                papers[i]["published"] = entry.get("published", "")
    except requests.RequestException:
        pass  # 摘要获取失败不影响主流程


def fetch_github_trending(since: str = "daily", language: str = "") -> List[Dict]:
    """从 GitHub Trending 获取热门仓库"""
    url = GITHUB_TRENDING_URL
    if language:
        url += f"/{language}"
    url += f"?since={since}"

    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    repos = []

    for article in soup.select("article.Box-row")[:10]:
        # 仓库名
        h2 = article.select_one("h2 a")
        if not h2:
            continue
        full_name = h2.get("href", "").strip("/")

        # 描述
        desc_elem = article.select_one("p")
        description = desc_elem.text.strip() if desc_elem else ""

        # 语言
        lang_elem = article.select_one("[itemprop='programmingLanguage']")
        lang = lang_elem.text.strip() if lang_elem else ""

        # Star 数
        stars = 0
        stars_link = article.find("a", href=lambda h: h and "stargazers" in h)
        if stars_link:
            stars_text = stars_link.get_text(strip=True).replace(",", "")
            stars = int(re.search(r"\d+", stars_text).group()) if re.search(r"\d+", stars_text) else 0

        # 今日新增 star
        today_stars = 0
        for text in article.find_all(string=lambda s: s and "stars today" in s.lower()):
            match = re.search(r"([\d,]+)\s+stars?\s+today", text)
            if match:
                today_stars = int(match.group(1).replace(",", ""))

        repos.append({
            "name": full_name,
            "url": f"https://github.com/{full_name}",
            "description": description,
            "language": lang,
            "stars": stars,
            "today_stars": today_stars,
            "source": "github_trending"
        })

    return repos


def fetch_hackernews(top_n: int = 10) -> List[Dict]:
    """从 Hacker News 获取最新热门帖子"""
    resp = requests.get(HN_TOP_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    top_ids = resp.json()[:top_n]

    stories = []
    for story_id in top_ids:
        try:
            r = requests.get(HN_ITEM_URL.format(story_id), headers=HEADERS, timeout=15)
            r.raise_for_status()
            item = r.json()
            if not item or item.get("type") != "story":
                continue
            title = item.get("title", "")
            # 只保留 AI/技术相关
            if not any(kw in title.lower() for kw in
                       ["ai", "llm", "gpt", "claude", "openai", "google", "meta",
                        "apple", "microsoft", "robot", "model", "transformer",
                        "agent", "neural", "deep", "code", "programming",
                        "startup", "python", "rust", "data"]):
                continue
            stories.append({
                "title": title,
                "url": item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                "score": item.get("score", 0),
                "by": item.get("by", ""),
                "source": "hackernews",
            })
        except Exception:
            continue

    return stories


def fetch_tech_news(max_results: int = 5) -> List[Dict]:
    """从 RSS 聚合 AI 科技新闻（TechCrunch + ArsTechnica）"""
    rss_feeds = [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://feeds.arstechnica.com/arstechnica/index",
    ]
    items = []
    seen_urls = set()

    for feed_url in rss_feeds:
        try:
            # 先用 requests 获取原始 XML（避免 SSL 问题）
            resp = requests.get(feed_url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
        except Exception:
            continue

        for entry in feed.entries:
            url = entry.get("link", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            # 清理 HTML 标签
            summary_clean = re.sub(r"<[^>]+>", "", summary)[:200]

            items.append({
                "title": title,
                "url": url,
                "description": summary_clean,
                "source": "tech_news"
            })
            if len(items) >= max_results:
                break
        if len(items) >= max_results:
            break

    return items[:max_results]


def fetch_huggingface(max_results: int = 5) -> List[Dict]:
    """从 Hugging Face Daily Papers 获取最新论文"""
    url = "https://huggingface.co/papers"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    papers = []

    # HF papers 页面：每篇论文在 article 标签内
    for article in soup.select("article")[:max_results]:
        link = article.select_one("a[href*='/papers/']")
        if not link:
            continue
        title = link.text.strip()
        href = link.get("href", "")
        paper_url = f"https://huggingface.co{href}" if href.startswith("/") else href

        # 描述/摘要
        desc_elem = article.select_one("p")
        description = desc_elem.text.strip()[:300] if desc_elem else ""

        papers.append({
            "title": title,
            "url": paper_url,
            "description": description,
            "source": "huggingface"
        })

    return papers


def fetch_all(max_arxiv: int = 8, max_hn: int = 30,
              max_ph: int = 5, max_hf: int = 5) -> Dict[str, List[Dict]]:
    """抓取所有数据源，返回聚合结果"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    papers = fetch_arxiv(max_results=max_arxiv)
    repos = fetch_github_trending()
    stories = fetch_hackernews(top_n=max_hn)
    tech = fetch_tech_news(max_results=max_ph)
    hf_papers = fetch_huggingface(max_results=max_hf)

    return {
        "date": now,
        "arxiv_papers": papers,
        "github_trending": repos,
        "hackernews": stories,
        "tech_news": tech,
        "huggingface": hf_papers,
    }


if __name__ == "__main__":
    import json
    data = fetch_all()
    print(json.dumps(data, ensure_ascii=False, indent=2))
