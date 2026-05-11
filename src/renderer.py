"""HTML 渲染模块：将 Markdown 日报转为美观的 HTML 页面"""

import re
import json
import os
from datetime import datetime
from typing import Optional, List


ARCHIVE_INDEX = "output/reports.json"


DAILY_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 日报 - {date}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{ primary: '#6366f1', accent: '#06b6d4' }},
                    fontFamily: {{ sans: ['-apple-system', 'BlinkMacSystemFont', '"Noto Sans SC"', '"Segoe UI"', 'Roboto', 'sans-serif'] }},
                }}
            }}
        }}
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        body {{ font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif; }}
        code {{ font-family: 'JetBrains Mono', monospace; }}
        .section-card {{
            background: white; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
        }}
        .source-badge {{
            display: inline-flex; align-items: center; padding: 2px 10px; border-radius: 999px;
            font-size: 0.75rem; font-weight: 600; white-space: nowrap;
        }}
        .key-point {{
            padding: 1rem 1.25rem; margin-bottom: 0.75rem; border-radius: 12px;
            background: linear-gradient(135deg, #f8f9ff 0%, #f0f1ff 100%);
            border-left: 4px solid #6366f1;
        }}
        .key-point:last-child {{ margin-bottom: 0; }}
        .item-card {{
            padding: 0.875rem 1rem; margin-bottom: 0.625rem; border-radius: 10px;
            border: 1px solid #f0f0f0;
        }}
        .item-card:hover {{ border-color: #e0e0ff; background: #fafaff; }}
        .item-card:last-child {{ margin-bottom: 0; }}
        .editor-note {{
            background: linear-gradient(135deg, #fef9f0 0%, #fff4e6 100%);
            border-radius: 12px; padding: 1.25rem; border-left: 4px solid #f59e0b;
        }}
        .nav-btn {{
            display: inline-flex; align-items: center; gap: 0.25rem;
            padding: 0.5rem 1rem; border-radius: 10px; font-size: 0.875rem;
            background: white; border: 1px solid #e5e7eb;
            transition: all 0.15s;
        }}
        .nav-btn:hover {{ border-color: #6366f1; color: #6366f1; }}
        @media (prefers-color-scheme: dark) {{
            .section-card {{ background: #1e1e2e; }}
            .key-point {{ background: linear-gradient(135deg, #1a1a2e 0%, #1e1e3a 100%); }}
            .item-card {{ border-color: #2a2a3e; }}
            .item-card:hover {{ border-color: #4a4a6e; background: #22223a; }}
            .editor-note {{ background: linear-gradient(135deg, #2a2010 0%, #1e1a0e 100%); }}
            .nav-btn {{ background: #1e1e2e; border-color: #2a2a3e; }}
            .nav-btn:hover {{ border-color: #6366f1; }}
        }}
        @media (max-width: 640px) {{ .section-card {{ padding: 1rem; }} .key-point {{ padding: 0.75rem 1rem; }} }}
    </style>
</head>
<body class="bg-[#f6f8fc] text-gray-800 dark:bg-[#0f0f1a] dark:text-gray-200">
    <div class="max-w-3xl mx-auto px-4 py-6 md:py-10">

        <!-- 头部 -->
        <header class="mb-6">
            <div class="bg-gradient-to-br from-indigo-600 via-indigo-500 to-cyan-400 rounded-2xl p-5 md:p-7 text-white">
                <div class="flex items-center justify-between mb-2">
                    <a href="/ai-daily/" class="hover:opacity-80 transition-opacity">
                        <h1 class="text-xl md:text-2xl font-bold tracking-tight">AI 日报</h1>
                    </a>
                    <a href="/ai-daily/archive.html" class="bg-white/20 backdrop-blur-sm text-white text-xs px-3 py-1.5 rounded-full font-medium hover:bg-white/30 transition">
                        历史归档
                    </a>
                </div>
                <p class="text-white/80 text-sm">{date}</p>
            </div>
            <!-- 日期导航 -->
            <div class="flex items-center justify-between mt-4">
                {nav_prev}
                <a href="/ai-daily/archive.html" class="text-xs text-gray-400 hover:text-indigo-500 transition">
                    查看全部日期
                </a>
                {nav_next}
            </div>
        </header>

        <!-- 内容 -->
        {content_html}

        <!-- 底部 -->
        <footer class="mt-10 pt-6 border-t border-gray-200 dark:border-gray-800 text-center">
            <p class="text-sm text-gray-400">
                由 AI 自动生成 · 数据来源 arXiv / GitHub / Hacker News
            </p>
            <p class="text-xs text-gray-300 mt-1">
                <a href="https://github.com/RexChen595223656/ai-daily" class="hover:text-indigo-500 transition" target="_blank" rel="noopener">
                    GitHub → RexChen595223656/ai-daily
                </a>
            </p>
            {nav_bottom}
        </footer>
    </div>
</body>
</html>"""


ARCHIVE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 日报 - 历史归档</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{ primary: '#6366f1', accent: '#06b6d4' }},
                    fontFamily: {{ sans: ['-apple-system', 'BlinkMacSystemFont', '"Noto Sans SC"', '"Segoe UI"', 'Roboto', 'sans-serif'] }},
                }}
            }}
        }}
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap');
        body {{ font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif; }}
    </style>
</head>
<body class="bg-[#f6f8fc] text-gray-800 dark:bg-[#0f0f1a] dark:text-gray-200">
    <div class="max-w-3xl mx-auto px-4 py-6 md:py-10">

        <!-- 头部 -->
        <header class="mb-8">
            <div class="bg-gradient-to-br from-indigo-600 via-indigo-500 to-cyan-400 rounded-2xl p-6 md:p-8 text-white">
                <div class="flex items-center justify-between mb-2">
                    <a href="/ai-daily/" class="hover:opacity-80 transition-opacity">
                        <h1 class="text-2xl md:text-3xl font-bold tracking-tight">AI 日报</h1>
                    </a>
                    <span class="bg-white/20 backdrop-blur-sm text-white text-xs px-3 py-1.5 rounded-full font-medium">
                        历史归档
                    </span>
                </div>
                <p class="text-white/80 text-sm mt-1">共 {count} 期 · 每天更新</p>
            </div>
        </header>

        <!-- 日期列表 -->
        <div class="section-card bg-white dark:bg-[#1e1e2e] rounded-2xl p-6 shadow-sm">
            <h2 class="text-lg font-bold mb-5 text-gray-900 dark:text-gray-100">📅 往期日报</h2>
            <div class="space-y-2">
                {list_items}
            </div>
        </div>

        <footer class="mt-10 pt-6 border-t border-gray-200 dark:border-gray-800 text-center">
            <p class="text-sm text-gray-400">由 AI 自动生成 · 每天更新</p>
        </footer>
    </div>
</body>
</html>"""


SECTION_ICONS = {
    "📌 今日要点": "📌",
    "📄 论文精读": "📄",
    "⭐ 热门开源": "⭐",
    "🛠 科技新闻": "🛠",
    "💬 社区热议": "💬",
    "🤖 编辑点评": "🤖",
}

SECTION_CLASS = {
    "📌": "section-card",
    "📄": "section-card",
    "⭐": "section-card",
    "🛠": "section-card",
    "💬": "section-card",
    "🤖": "editor-note",
}


def _wrap_section(title: str, body_html: str) -> str:
    icon = ""
    for emoji, _ in SECTION_ICONS.items():
        if title.startswith(emoji):
            icon = emoji[0]
            break
    card_class = SECTION_CLASS.get(icon, "section-card")
    return f"""<div class="{card_class}">
    <h2 class="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">{title}</h2>
    <div class="space-y-1">
{body_html}
    </div>
</div>"""


def markdown_to_html(md_text: str) -> str:
    html = md_text
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong class="font-semibold">\1</strong>', html)
    html = re.sub(r'`([^`]+?)`',
                  r'<code class="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-sm font-mono text-pink-600 dark:text-pink-400">\1</code>', html)

    def _replace_link(m):
        text = m.group(1)
        url = m.group(2)
        badge_colors = {
            "arXiv": "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300",
            "GitHub": "bg-gray-50 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
            "Hacker News": "bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
        }
        if text in badge_colors:
            return f'<a href="{url}" target="_blank" rel="noopener" class="source-badge {badge_colors[text]} hover:opacity-80 transition-opacity">{text} ↗</a>'
        return f'<a href="{url}" target="_blank" rel="noopener" class="text-indigo-600 dark:text-indigo-400 hover:underline font-medium">{text}</a>'
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', _replace_link, html)

    lines = html.split("\n")
    result = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        h1_match = re.match(r'^#\s+(.+)$', stripped)
        if h1_match:
            result.append(f"<h1 class=\"text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6\">{h1_match.group(1)}</h1>")
            i += 1
            continue
        h2_match = re.match(r'^##\s+(.+)$', stripped)
        if h2_match:
            title = h2_match.group(1)
            i += 1
            section_lines = []
            while i < len(lines):
                next_line = lines[i].strip()
                if re.match(r'^#{1,2}\s+', next_line):
                    break
                section_lines.append(lines[i])
                i += 1
            section_html = _parse_section_content(section_lines, title)
            result.append(_wrap_section(title, section_html))
            continue
        i += 1
    return "\n".join(result)


def _parse_section_content(lines: list, section_title: str) -> str:
    html_parts = []
    is_key_points = "今日要点" in section_title
    is_editor_note = "编辑点评" in section_title
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            content = stripped[2:]
            if is_key_points:
                html_parts.append(f'<div class="key-point"><p class="text-sm leading-relaxed text-gray-700 dark:text-gray-300">{content}</p></div>')
            elif is_editor_note:
                html_parts.append(f'<p class="text-sm leading-relaxed">{content}</p>')
            else:
                html_parts.append(f'<div class="item-card"><p class="text-sm leading-relaxed text-gray-700 dark:text-gray-300">{content}</p></div>')
            continue
        content = re.sub(r'^\d+\.\s+', '', stripped)
        html_parts.append(f'<p class="text-sm leading-relaxed text-gray-700 dark:text-gray-300">{content}</p>')
    return "\n".join(html_parts)


def _read_archive() -> List[str]:
    """读取历史归档索引"""
    if os.path.exists(ARCHIVE_INDEX):
        try:
            with open(ARCHIVE_INDEX, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _write_archive(dates: List[str]):
    """写入历史归档索引"""
    os.makedirs(os.path.dirname(ARCHIVE_INDEX) or ".", exist_ok=True)
    with open(ARCHIVE_INDEX, "w") as f:
        json.dump(dates, f, ensure_ascii=False)


def update_archive(date_str: str):
    """更新归档索引：添加新日期，去重排序"""
    dates = _read_archive()
    if date_str not in dates:
        dates.append(date_str)
    dates = sorted(set(dates), reverse=True)
    _write_archive(dates)
    return dates


def get_nav(date_str: str, dates: List[str]) -> tuple:
    """获取 prev/next 日期用于导航"""
    try:
        idx = dates.index(date_str)
    except ValueError:
        return "", "", ""
    prev_date = dates[idx + 1] if idx + 1 < len(dates) else None
    next_date = dates[idx - 1] if idx - 1 >= 0 else None

    def _btn(label, d, direction):
        if not d:
            return f'<span class="nav-btn opacity-30 cursor-not-allowed">{label}</span>'
        return f'<a href="daily-{d}.html" class="nav-btn">{label}</a>'

    nav_prev = _btn("← 前一日", next_date if direction == "next" else prev_date, "")
    nav_next = _btn("后一日 →", prev_date, "next")

    # 修正方向
    prev_btn = _btn("← 前一日", prev_date, "")
    next_btn = _btn("后一日 →", next_date, "")
    bottom = f'<div class="flex justify-center gap-4 mt-4">{prev_btn}{next_btn}</div>' if (prev_date or next_date) else ""

    return prev_btn, next_btn, bottom


def render_daily(md_content: str, date: str, prev_date: str = "", next_date: str = "") -> str:
    """渲染单期日报"""
    content_html = markdown_to_html(md_content)

    def _btn(label, d, is_prev):
        if not d:
            return f'<span class="nav-btn opacity-30 cursor-not-allowed">{label}</span>'
        return f'<a href="daily-{d}.html" class="nav-btn">{label}</a>'

    prev_btn = _btn("← 前一日", prev_date, True)
    next_btn = _btn("后一日 →", next_date, False)
    nav_bottom = f'<div class="flex justify-center gap-3 mt-3">{prev_btn}{next_btn}</div>' if (prev_date or next_date) else ""

    return DAILY_TEMPLATE.format(
        date=date, content_html=content_html,
        nav_prev=prev_btn, nav_next=next_btn, nav_bottom=nav_bottom
    )


def render_archive(dates: List[str]) -> str:
    """渲染历史归档页"""
    items = []
    for d in dates:
        items.append(
            f'<a href="daily-{d}.html" '
            f'class="flex items-center justify-between p-3 rounded-xl hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition group">'
            f'<span class="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-indigo-600 dark:group-hover:text-indigo-400">📅 {d}</span>'
            f'<span class="text-xs text-gray-400 group-hover:text-indigo-400">→</span>'
            f'</a>'
        )
    return ARCHIVE_TEMPLATE.format(count=len(dates), list_items="\n".join(items))


def save_html(md_content: str, output_path: str, date: str = "",
              prev_date: str = "", next_date: str = "") -> str:
    """生成 HTML 文件并保存"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    html = render_daily(md_content, date, prev_date, next_date)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 日报已生成: {output_path}")
    return output_path


def save_archive(dates: List[str]):
    """生成并保存归档页面"""
    html = render_archive(dates)
    path = "output/archive.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 归档页已生成: {path}")
