"""HTML 渲染模块：将 Markdown 日报转为美观的 HTML 页面"""

import re
import json
import os
import email.utils
from datetime import datetime, timezone
from typing import Optional, List, Dict


ARCHIVE_INDEX = "output/reports.json"


DAILY_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 日报 - {date}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: { primary: '#6366f1', accent: '#06b6d4' },
                    fontFamily: { sans: ['-apple-system', 'BlinkMacSystemFont', '"Noto Sans SC"', '"Segoe UI"', 'Roboto', 'sans-serif'] },
                }
            }
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        * { transition: background-color 0.2s ease, border-color 0.2s ease; }
        body { font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif; }
        code { font-family: 'JetBrains Mono', monospace; }
        .section-card { background: white; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06); }
        .source-badge { display: inline-flex; align-items: center; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; white-space: nowrap; }
        .key-point { padding: 1rem 1.25rem; margin-bottom: 0.75rem; border-radius: 12px; background: linear-gradient(135deg, #f8f9ff 0%, #f0f1ff 100%); border-left: 4px solid #6366f1; }
        .key-point:last-child { margin-bottom: 0; }
        .item-card { padding: 0.875rem 1rem; margin-bottom: 0.625rem; border-radius: 10px; border: 1px solid #f0f0f0; }
        .item-card:hover { border-color: #e0e0ff; background: #fafaff; }
        .item-card:last-child { margin-bottom: 0; }
        .editor-note { background: linear-gradient(135deg, #fef9f0 0%, #fff4e6 100%); border-radius: 12px; padding: 1.25rem; border-left: 4px solid #f59e0b; }
        .nav-btn { display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.5rem 1rem; border-radius: 10px; font-size: 0.875rem; background: white; border: 1px solid #e5e7eb; transition: all 0.15s; }
        .nav-btn:hover { border-color: #6366f1; color: #6366f1; }
        .toolbar-btn { display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: 10px; cursor: pointer; transition: all 0.15s; user-select: none; }
        .toolbar-btn:hover { background: rgba(255,255,255,0.2); }
        .font-btn { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 6px; cursor: pointer; font-weight: 600; transition: all 0.15s; }
        .font-btn:hover { background: rgba(255,255,255,0.2); }
        .font-btn.active { background: rgba(255,255,255,0.25); }
        #backToTop { position: fixed; bottom: 24px; right: 24px; width: 44px; height: 44px; border-radius: 50%; background: #6366f1; color: white; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 4px 12px rgba(99,102,241,0.3); opacity: 0; transform: translateY(20px); transition: all 0.3s; z-index: 50; }
        #backToTop.show { opacity: 1; transform: translateY(0); }
        #backToTop:hover { box-shadow: 0 6px 20px rgba(99,102,241,0.4); transform: translateY(-2px); }
        .text-sm-body { font-size: 0.875rem; line-height: 1.7; }
        .text-base-body { font-size: 1rem; line-height: 1.75; }
        .text-lg-body { font-size: 1.125rem; line-height: 1.8; }
        @media (prefers-color-scheme: dark) {
            body:not(.light) .section-card, body.dark .section-card { background: #1e1e2e; }
            body:not(.light) .key-point, body.dark .key-point { background: linear-gradient(135deg, #1a1a2e 0%, #1e1e3a 100%); }
            body:not(.light) .item-card, body.dark .item-card { border-color: #2a2a3e; }
            body:not(.light) .item-card:hover, body.dark .item-card:hover { border-color: #4a4a6e; background: #22223a; }
            body:not(.light) .editor-note, body.dark .editor-note { background: linear-gradient(135deg, #2a2010 0%, #1e1a0e 100%); }
            body:not(.light) .nav-btn, body.dark .nav-btn { background: #1e1e2e; border-color: #2a2a3e; }
            body:not(.light) .nav-btn:hover, body.dark .nav-btn:hover { border-color: #6366f1; }
        }
        @media (max-width: 640px) { .section-card { padding: 1rem; } .key-point { padding: 0.75rem 1rem; } }
    </style>
</head>
<body class="bg-[#f6f8fc] text-gray-800 text-sm-body dark:bg-[#0f0f1a] dark:text-gray-200">
    <!-- 返回顶部 -->
    <div id="backToTop" onclick="window.scrollTo({top:0,behavior:'smooth'})">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 15l-6-6-6 6"/></svg>
    </div>

    <div class="max-w-3xl mx-auto px-4 py-6 md:py-10">

        <!-- 头部 -->
        <header class="mb-6">
            <div class="bg-gradient-to-br from-indigo-600 via-indigo-500 to-cyan-400 rounded-2xl p-5 md:p-7 text-white relative overflow-hidden">
                <div class="flex items-center justify-between mb-2">
                    <a href="/ai-daily/" class="hover:opacity-80 transition-opacity">
                        <h1 class="text-xl md:text-2xl font-bold tracking-tight">AI 日报</h1>
                    </a>
                    <div class="flex items-center gap-1">
                        <!-- 字体大小 -->
                        <span class="text-xs text-white/60 mr-1">字体</span>
                        <span class="font-btn text-xs" onclick="setFontSize('sm')" id="fs-sm">A</span>
                        <span class="font-btn text-sm" onclick="setFontSize('base')" id="fs-base">A</span>
                        <span class="font-btn text-base" onclick="setFontSize('lg')" id="fs-lg">A</span>
                        <span class="w-px h-5 bg-white/20 mx-1"></span>
                        <!-- 暗色模式 -->
                        <span class="toolbar-btn" onclick="toggleDark()" id="darkToggle" title="切换暗色模式">
                            <svg id="sunIcon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                            </svg>
                            <svg id="moonIcon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:none">
                                <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
                            </svg>
                        </span>
                        <a href="feed.xml" class="bg-orange-500/30 backdrop-blur-sm text-orange-200 text-xs px-2.5 py-1.5 rounded-full font-medium hover:bg-orange-500/50 transition">
                            RSS
                        </a>
                        <a href="/ai-daily/archive.html" class="bg-white/20 backdrop-blur-sm text-white text-xs px-3 py-1.5 rounded-full font-medium hover:bg-white/30 transition ml-1">
                            归档
                        </a>
                    </div>
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
        <div id="contentArea">
            {content_html}
        </div>

        <!-- 底部 -->
        <footer class="mt-10 pt-6 border-t border-gray-200 dark:border-gray-800 text-center">
            <p class="text-sm text-gray-400">
                由 AI 自动生成 · 数据来源 arXiv / GitHub / HN / Tech News
            </p>
            <p class="text-xs text-gray-300 mt-1">
                <a href="https://github.com/RexChen595223656/ai-daily" class="hover:text-indigo-500 transition" target="_blank" rel="noopener">
                    GitHub → RexChen595223656/ai-daily
                </a>
            </p>
            {nav_bottom}
        </footer>
    </div>

    <script>
        // 暗色模式
        function getTheme() { return localStorage.getItem('theme') || 'auto'; }
        function applyTheme(theme) {
            const d = document.documentElement;
            const sun = document.getElementById('sunIcon'), moon = document.getElementById('moonIcon');
            if (theme === 'dark') {
                d.classList.add('dark'); document.body.classList.remove('light'); document.body.classList.add('dark');
                sun.style.display = 'none'; moon.style.display = '';
            } else if (theme === 'light') {
                d.classList.remove('dark'); document.body.classList.remove('dark'); document.body.classList.add('light');
                sun.style.display = ''; moon.style.display = 'none';
            } else {
                d.classList.remove('dark'); document.body.classList.remove('dark','light');
                sun.style.display = ''; moon.style.display = 'none';
            }
        }
        function toggleDark() {
            const cur = getTheme();
            const next = cur === 'dark' ? 'light' : cur === 'light' ? 'auto' : 'dark';
            localStorage.setItem('theme', next);
            applyTheme(next);
        }
        applyTheme(getTheme());

        // 字体大小
        function setFontSize(size) {
            const el = document.getElementById('contentArea');
            el.classList.remove('text-sm-body', 'text-base-body', 'text-lg-body');
            el.classList.add('text-' + size + '-body');
            localStorage.setItem('fontSize', size);
            document.querySelectorAll('.font-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('fs-' + size).classList.add('active');
        }
        const savedFs = localStorage.getItem('fontSize') || 'sm';
        setFontSize(savedFs);

        // 返回顶部
        window.addEventListener('scroll', function() {
            document.getElementById('backToTop').classList.toggle('show', window.scrollY > 400);
        });
    </script>
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
        .search-box {{ transition: all 0.2s; }}
        .search-box:focus {{ box-shadow: 0 0 0 3px rgba(99,102,241,0.15); }}
        .hl {{ background: #fef08a; padding: 0 2px; border-radius: 2px; }}
        @media (prefers-color-scheme: dark) {{
            .hl {{ background: #854d0e; }}
        }}
    </style>
</head>
<body class="bg-[#f6f8fc] text-gray-800 dark:bg-[#0f0f1a] dark:text-gray-200">
    <div class="max-w-3xl mx-auto px-4 py-6 md:py-10">

        <header class="mb-8">
            <div class="bg-gradient-to-br from-indigo-600 via-indigo-500 to-cyan-400 rounded-2xl p-6 md:p-8 text-white">
                <div class="flex items-center justify-between mb-2">
                    <a href="/ai-daily/" class="hover:opacity-80 transition-opacity">
                        <h1 class="text-2xl md:text-3xl font-bold tracking-tight">AI 日报</h1>
                    </a>
                    <div class="flex items-center gap-2">
                        <a href="feed.xml" class="bg-orange-500/30 backdrop-blur-sm text-orange-200 text-xs px-3 py-1.5 rounded-full font-medium hover:bg-orange-500/50 transition">
                            RSS
                        </a>
                        <a href="/ai-daily/" class="bg-white/20 backdrop-blur-sm text-white text-xs px-3 py-1.5 rounded-full font-medium hover:bg-white/30 transition">
                            最新一期
                        </a>
                    </div>
                </div>
                <p class="text-white/80 text-sm mt-1">共 {count} 期 · 每天更新</p>
            </div>
        </header>

        <!-- 搜索框 -->
        <div class="mb-6">
            <input id="searchInput" type="text" placeholder="搜索日报内容（如：多智能体、RAG、本地部署）"
                   class="search-box w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e2e] text-sm text-gray-800 dark:text-gray-200 outline-none">
            <div class="text-xs text-gray-400 mt-1.5 ml-1">
                <span id="resultCount">共 {count} 期</span>
            </div>
        </div>

        <!-- 日期列表 + 搜索结果 -->
        <div class="section-card bg-white dark:bg-[#1e1e2e] rounded-2xl p-6 shadow-sm">
            <h2 class="text-lg font-bold mb-5 text-gray-900 dark:text-gray-100">📅 往期日报</h2>
            <div id="reportList" class="space-y-2">
                {list_items}
            </div>
            <div id="noResult" class="hidden text-center py-10 text-gray-400 text-sm">没有匹配的结果，试试其他关键词</div>
        </div>

        <footer class="mt-10 pt-6 border-t border-gray-200 dark:border-gray-800 text-center">
            <p class="text-sm text-gray-400">由 AI 自动生成 · 每天更新</p>
        </footer>
    </div>

    <script>
        let searchIndex = [];
        let allDates = [];

        fetch('search_index.json')
            .then(r => r.json())
            .then(data => {
                searchIndex = data;
                allDates = data.map(d => d.date);
            })
            .catch(() => {});

        document.getElementById('searchInput').addEventListener('input', function() {
            const q = this.value.trim().toLowerCase();
            const list = document.getElementById('reportList');
            const noRes = document.getElementById('noResult');
            const count = document.getElementById('resultCount');

            if (!q || searchIndex.length === 0) {
                list.innerHTML = '{list_items}';
                noRes.classList.add('hidden');
                count.textContent = '共 ' + allDates.length + ' 期';
                return;
            }

            const results = searchIndex.filter(item =>
                item.title.toLowerCase().includes(q) ||
                item.keywords.some(k => k.includes(q))
            );

            if (results.length === 0) {
                list.innerHTML = '';
                noRes.classList.remove('hidden');
                count.textContent = '未找到匹配结果';
                return;
            }

            noRes.classList.add('hidden');
            count.textContent = '找到 ' + results.length + ' 条结果';

            list.innerHTML = results.map(r => `
                <a href="daily-${r.date}.html" class="flex items-center justify-between p-3 rounded-xl hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition group">
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-indigo-600 dark:group-hover:text-indigo-400">📅 ${r.date}</span>
                    <span class="text-xs text-indigo-500 group-hover:text-indigo-400 ml-4 truncate max-w-[300px] text-right">${r.title}</span>
                </a>
            `).join('');
        });
    </script>
</body>
</html>"""


SECTION_ICONS = {
    "📌 今日趋势": "📌",
    "📄 论文精读": "📄",
    "⭐ 热门开源": "⭐",
    "🛠 科技新闻": "🛠",
    "💬 社区热议": "💬",
    "🤖 编辑点评": "🤖",
    "🤖 主编点评": "🤖",
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
    is_key_points = "今日趋势" in section_title or "今日要点" in section_title
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

    def _btn(label, d):
        if not d:
            return f'<span class="nav-btn opacity-30 cursor-not-allowed">{label}</span>'
        return f'<a href="daily-{d}.html" class="nav-btn">{label}</a>'

    prev_btn = _btn("← 前一日", prev_date)
    next_btn = _btn("后一日 →", next_date)
    nav_bottom = f'<div class="flex justify-center gap-3 mt-3">{prev_btn}{next_btn}</div>' if (prev_date or next_date) else ""

    html = DAILY_TEMPLATE
    for k, v in [("{date}", date), ("{content_html}", content_html),
                 ("{nav_prev}", prev_btn), ("{nav_next}", next_btn),
                 ("{nav_bottom}", nav_bottom)]:
        html = html.replace(k, v)
    return html


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
    return ARCHIVE_TEMPLATE.replace("{count}", str(len(dates))).replace("{list_items}", "\n".join(items))


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


def render_rss(items: List[Dict]) -> str:
    """生成 RSS feed XML"""
    now_rfc = email.utils.format_datetime(datetime.now(timezone.utc))
    entries = []
    for item in items[:20]:  # 最多 20 条
        date_str = item["date"]
        title = item.get("title", f"AI 日报 - {date_str}")
        desc = item.get("summary", title)
        desc_escaped = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        title_escaped = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        pub_date = email.utils.format_datetime(
            datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        )
        entries.append(f"""    <item>
      <title>{title_escaped}</title>
      <link>https://rexchen595223656.github.io/ai-daily/daily-{date_str}.html</link>
      <description><![CDATA[{desc}]]></description>
      <pubDate>{pub_date}</pubDate>
      <guid>https://rexchen595223656.github.io/ai-daily/daily-{date_str}.html</guid>
    </item>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>AI 日报</title>
    <description>每天聚合 arXiv / GitHub / Hacker News / 科技新闻，AI 生成摘要</description>
    <link>https://rexchen595223656.github.io/ai-daily/</link>
    <atom:link href="https://rexchen595223656.github.io/ai-daily/feed.xml" rel="self" type="application/rss+xml"/>
    <language>zh-CN</language>
    <lastBuildDate>{now_rfc}</lastBuildDate>
{chr(10).join(entries)}
  </channel>
</rss>"""


def save_rss(items: List[Dict]):
    """生成并保存 RSS feed"""
    xml = render_rss(items)
    path = "output/feed.xml"
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"✅ RSS 已生成: {path}")


def save_archive(dates: List[str]):
    """生成并保存归档页面"""
    html = render_archive(dates)
    path = "output/archive.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 归档页已生成: {path}")
