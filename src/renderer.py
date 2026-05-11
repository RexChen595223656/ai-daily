"""HTML 渲染模块：将 Markdown 日报转为美观的 HTML 页面"""

import re
from datetime import datetime
from typing import Optional


HTML_TEMPLATE = """<!DOCTYPE html>
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
                    colors: {{
                        primary: '{{"#6366f1"}}',
                        accent: '{{"#06b6d4"}}',
                    }},
                    fontFamily: {{
                        sans: ['-apple-system', 'BlinkMacSystemFont', '"Noto Sans SC"', '"Segoe UI"', 'Roboto', 'sans-serif'],
                    }},
                }}
            }}
        }}
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        body {{ font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif; }}
        code {{ font-family: 'JetBrains Mono', monospace; }}

        .section-card {{
            background: white;
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
            transition: box-shadow 0.2s ease;
        }}
        .section-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.06), 0 2px 4px rgba(0,0,0,0.04);
        }}

        .source-badge {{
            display: inline-flex;
            align-items: center;
            padding: 2px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            white-space: nowrap;
        }}

        .key-point {{
            padding: 1rem 1.25rem;
            margin-bottom: 0.75rem;
            border-radius: 12px;
            background: linear-gradient(135deg, #f8f9ff 0%, #f0f1ff 100%);
            border-left: 4px solid #6366f1;
        }}

        .key-point:last-child {{ margin-bottom: 0; }}

        .item-card {{
            padding: 0.875rem 1rem;
            margin-bottom: 0.625rem;
            border-radius: 10px;
            border: 1px solid #f0f0f0;
            transition: border-color 0.2s, background 0.2s;
        }}
        .item-card:hover {{
            border-color: #e0e0ff;
            background: #fafaff;
        }}
        .item-card:last-child {{ margin-bottom: 0; }}

        .editor-note {{
            background: linear-gradient(135deg, #fef9f0 0%, #fff4e6 100%);
            border-radius: 12px;
            padding: 1.25rem;
            border-left: 4px solid #f59e0b;
        }}

        @media (prefers-color-scheme: dark) {{
            .section-card {{
                background: #1e1e2e;
                box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            }}
            .key-point {{
                background: linear-gradient(135deg, #1a1a2e 0%, #1e1e3a 100%);
            }}
            .item-card {{
                border-color: #2a2a3e;
            }}
            .item-card:hover {{
                border-color: #4a4a6e;
                background: #22223a;
            }}
            .editor-note {{
                background: linear-gradient(135deg, #2a2010 0%, #1e1a0e 100%);
            }}
        }}

        @media (max-width: 640px) {{
            .section-card {{ padding: 1rem; border-radius: 12px; }}
            .key-point {{ padding: 0.75rem 1rem; }}
        }}
    </style>
</head>
<body class="bg-[#f6f8fc] text-gray-800 dark:bg-[#0f0f1a] dark:text-gray-200">
    <div class="max-w-3xl mx-auto px-4 py-6 md:py-10">

        <!-- 头部 -->
        <header class="mb-8">
            <div class="bg-gradient-to-br from-indigo-600 via-indigo-500 to-cyan-400 rounded-2xl p-6 md:p-8 text-white">
                <div class="flex items-center justify-between mb-3">
                    <h1 class="text-2xl md:text-3xl font-bold tracking-tight">AI 日报</h1>
                    <span class="bg-white/20 backdrop-blur-sm text-white text-xs px-3 py-1.5 rounded-full font-medium">
                        AI Daily
                    </span>
                </div>
                <p class="text-white/80 text-sm md:text-base">{date}</p>
                <div class="mt-4 flex flex-wrap gap-2 text-xs text-white/70">
                    <span class="bg-white/10 px-2.5 py-1 rounded-full">📄 arXiv 论文</span>
                    <span class="bg-white/10 px-2.5 py-1 rounded-full">⭐ GitHub Trending</span>
                    <span class="bg-white/10 px-2.5 py-1 rounded-full">💬 Hacker News</span>
                </div>
            </div>
        </header>

        <!-- 内容 -->
        {content_html}

        <!-- 底部 -->
        <footer class="mt-10 pt-6 border-t border-gray-200 dark:border-gray-800 text-center">
            <p class="text-sm text-gray-400">
                由 AI 自动生成 · 数据来源 arXiv / GitHub / Hacker News
            </p>
            <p class="text-xs text-gray-300 mt-2">
                <a href="https://github.com/RexChen595223656/ai-daily" class="hover:text-primary transition-colors" target="_blank" rel="noopener">
                    GitHub → RexChen595223656/ai-daily
                </a>
            </p>
        </footer>
    </div>
</body>
</html>"""

# 每个 section 标题对应的图标
SECTION_ICONS = {
    "📌 今日要点": "📌",
    "📄 论文精读": "📄",
    "⭐ 热门开源": "⭐",
    "💬 社区热议": "💬",
    "🤖 编辑点评": "🤖",
}

# 标题对应的卡片样式
SECTION_CLASS = {
    "📌": "section-card",
    "📄": "section-card",
    "⭐": "section-card",
    "💬": "section-card",
    "🤖": "editor-note",
}


def _wrap_section(title: str, body_html: str) -> str:
    """将 section 标题和内容包裹在卡片中"""
    # 提取 emoji 前缀来判断样式
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
    """将 Markdown 格式的日报转为结构化 HTML"""
    html = md_text

    # 加粗 **text**
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong class="font-semibold">\1</strong>', html)

    # 行内代码 `code`
    html = re.sub(r'`([^`]+?)`',
                  r'<code class="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-sm font-mono text-pink-600 dark:text-pink-400">\1</code>',
                  html)

    # Markdown 链接 [text](url) - 给特定来源加 badge
    def _replace_link(m):
        text = m.group(1)
        url = m.group(2)
        # 给来源标签加 badge 样式
        badge_colors = {
            "arXiv": "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300",
            "GitHub": "bg-gray-50 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
            "Hacker News": "bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
        }
        if text in badge_colors:
            return f'<a href="{url}" target="_blank" rel="noopener" class="source-badge {badge_colors[text]} hover:opacity-80 transition-opacity">{text} ↗</a>'
        return f'<a href="{url}" target="_blank" rel="noopener" class="text-indigo-600 dark:text-indigo-400 hover:underline font-medium">{text}</a>'
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', _replace_link, html)

    # 按行解析
    lines = html.split("\n")
    result = []
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        # Section 标题：一级标题
        h1_match = re.match(r'^#\s+(.+)$', stripped)
        if h1_match:
            result.append(f"<h1 class=\"text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6\">{h1_match.group(1)}</h1>")
            i += 1
            continue

        # 二级标题（section 标题）
        h2_match = re.match(r'^##\s+(.+)$', stripped)
        if h2_match:
            title = h2_match.group(1)
            # 收集此 section 内所有内容直到下一个标题或末尾
            i += 1
            section_lines = []
            while i < len(lines):
                next_line = lines[i].strip()
                if re.match(r'^#{1,2}\s+', next_line):
                    break
                section_lines.append(lines[i])
                i += 1

            # 处理 section 内的内容
            section_html = _parse_section_content(section_lines, title)
            result.append(_wrap_section(title, section_html))
            continue

        i += 1

    return "\n".join(result)


def _parse_section_content(lines: list, section_title: str) -> str:
    """解析 section 内的行内容"""
    html_parts = []
    in_list = False
    is_key_points = "今日要点" in section_title
    is_editor_note = "编辑点评" in section_title

    for line in lines:
        stripped = line.strip()

        # 空行
        if not stripped:
            continue

        # 无序列表
        if stripped.startswith("- "):
            content = stripped[2:]

            if is_key_points:
                # 今日要点用突出样式
                html_parts.append(f'<div class="key-point"><p class="text-sm leading-relaxed text-gray-700 dark:text-gray-300">{content}</p></div>')
            elif is_editor_note:
                html_parts.append(f'<p class="text-sm leading-relaxed">{content}</p>')
            else:
                # 普通列表项用 item-card
                html_parts.append(f'<div class="item-card"><p class="text-sm leading-relaxed text-gray-700 dark:text-gray-300">{content}</p></div>')
            continue

        # 段落
        content = re.sub(r'^\d+\.\s+', '', stripped)  # 去掉 "1. " 编号前缀
        html_parts.append(f'<p class="text-sm leading-relaxed text-gray-700 dark:text-gray-300">{content}</p>')

    return "\n".join(html_parts)


def render(md_content: str, date: Optional[str] = None) -> str:
    """将 Markdown 日报渲染为完整 HTML 页面"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    content_html = markdown_to_html(md_content)
    return HTML_TEMPLATE.format(date=date, content_html=content_html)


def save_html(md_content: str, output_path: Optional[str] = None) -> str:
    """生成 HTML 文件并保存"""
    if not output_path:
        date = datetime.now().strftime("%Y-%m-%d")
        output_path = f"output/daily-{date}.html"

    html = render(md_content)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 日报已生成: {output_path}")
    return output_path
