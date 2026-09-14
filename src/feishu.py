import time
import hmac
import hashlib
import base64
import httpx
from typing import List, Dict, Any, Optional

def generate_feishu_sign(secret: str, timestamp: int) -> str:
    """
    飞书自定义机器人安全校验：HMAC-SHA256 签名生成
    """
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")

def send_feishu_card(
    webhook_url: str,
    items: List[Dict[str, Any]],
    date_str: str,
    secret: Optional[str] = None
) -> bool:
    """
    向飞书群机器人发送定制的高颜值富文本交互式卡片
    """
    if not webhook_url:
        print("[Feishu] 未提供 FEISHU_WEBHOOK_URL，跳过发送")
        return False

    elements = []

    # 1. 顶部导语
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": (
                f"📅 **昨日速览**：聚合 AI、开源、硬件与极客热点，过滤低质量重复信息。"
                f"经 Gemini Flash 智能研判，为你精选以下 **{len(items)}** 条核心动态："
            )
        }
    })
    elements.append({"tag": "hr"})

    # 2. 项目列表
    for it in items:
        category = it.get("category", "🛠️ [开发神器]")
        title = it.get("title", "未知项目")
        url = it.get("url", "#")
        metric = it.get("metric", "")
        tag = it.get("tag", "🆕 新上榜")
        summary = it.get("summary", "")
        audience = it.get("target_audience", "开发者")
        stars = it.get("stars", "⭐⭐⭐⭐")
        source = it.get("source", "聚合资讯")

        card_content = (
            f"**{category}**  `{tag}`\n"
            f"🔗 **[{title}]({url})**  {metric}  {stars}\n"
            f"🗂️ **来源**：`{source}`\n"
            f"💡 **一句话**：{summary}\n"
            f"🎯 **适合对象**：`{audience}`"
        )

        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": card_content
            }
        })
        elements.append({"tag": "hr"})

    # 3. 底部操作按钮
    elements.append({
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": "🌐 查看 AIHot 实时热点榜"
                },
                "type": "primary",
                "url": "https://aihot.news/"
            }
        ]
    })

    card_payload: Dict[str, Any] = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📡 AI 趋势雷达 · 昨日晨报 ({date_str})"
                },
                "template": "blue"
            },
            "elements": elements
        }
    }

    # 如果配置了签名校验
    if secret:
        now_ts = int(time.time())
        card_payload["timestamp"] = str(now_ts)
        card_payload["sign"] = generate_feishu_sign(secret, now_ts)

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(webhook_url, json=card_payload)
            res_data = resp.json()
            if resp.status_code == 200 and res_data.get("code") == 0:
                print(f"[Feishu] 消息卡片发送成功！状态码: {resp.status_code}")
                return True
            else:
                print(f"[Feishu] 消息发送响应异常: {res_data}")
                return False
    except Exception as e:
        print(f"[Feishu] 发送飞书消息失败: {e}")
        return False
