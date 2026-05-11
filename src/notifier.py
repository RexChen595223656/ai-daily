"""推送模块：日报生成后推送到微信/飞书"""

import os
import json
import requests
from typing import Optional


def _get_title() -> str:
    from datetime import datetime
    return f"🤖 AI 日报 {datetime.now().strftime('%Y-%m-%d')}"


def _truncate_md(md: str, max_len: int = 2000) -> str:
    """截断过长内容，保留关键部分"""
    if len(md) <= max_len:
        return md
    # 保留开头部分（今日要点和论文）
    return md[:max_len] + "\n\n...（完整内容请查看网页）"


def push_serverchan(md_content: str, url: str = "") -> bool:
    """通过 Server 酱推送到微信"""
    key = os.getenv("SERVERCHAN_KEY")
    if not key:
        print("⚠️ 推送失败：SERVERCHAN_KEY 未设置")
        return False

    title = _get_title()
    content = _truncate_md(md_content, 3000)
    if url:
        content += f"\n\n[📖 查看完整日报]({url})"

    try:
        resp = requests.post(
            f"https://sctapi.ftqq.com/{key}.send",
            data={"title": title, "desp": content},
            timeout=15,
        )
        data = resp.json()
        if data.get("code") == 0:
            print(f"✅ 微信推送成功（Server 酱）")
            return True
        else:
            print(f"⚠️ 微信推送失败：{data.get('message', 'unknown')}")
            return False
    except Exception as e:
        print(f"⚠️ 微信推送异常：{e}")
        return False


def push_feishu(md_content: str, url: str = "") -> bool:
    """通过飞书 Webhook 推送到飞书群"""
    webhook = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook:
        print("⚠️ 推送失败：FEISHU_WEBHOOK_URL 未设置")
        return False

    title = _get_title()
    content = _truncate_md(md_content, 5000)

    # 飞书消息卡片
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "indigo",
            },
            "elements": [
                {"tag": "markdown", "content": content},
            ],
        },
    }

    if url:
        payload["card"]["elements"].append({
            "tag": "action",
            "actions": [
                {"tag": "button", "text": {"tag": "plain_text", "content": "📖 查看完整日报"},
                 "url": url, "type": "default"}
            ],
        })

    try:
        resp = requests.post(webhook, json=payload, timeout=15)
        data = resp.json()
        if data.get("code") == 0:
            print(f"✅ 飞书推送成功")
            return True
        else:
            print(f"⚠️ 飞书推送失败：{data.get('msg', 'unknown')}")
            return False
    except Exception as e:
        print(f"⚠️ 飞书推送异常：{e}")
        return False


def push(md_content: str, page_url: str = "") -> bool:
    """根据环境变量配置推送"""
    channel = os.getenv("PUSH_CHANNEL", "").strip().lower()

    if not channel:
        return False

    if channel == "serverchan":
        return push_serverchan(md_content, page_url)
    elif channel in ("feishu", "lark"):
        return push_feishu(md_content, page_url)
    else:
        print(f"⚠️ 未知推送渠道: {channel}（支持: serverchan / feishu）")
        return False
