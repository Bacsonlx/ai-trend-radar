import os
import json
import httpx
from typing import List, Dict, Any

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

PROMPT_TEMPLATE = """你是一名资深 AI 架构师兼前沿技术观察员。
请根据以下从 hype.replicate.dev 抓取的过去 24 小时最热门的 AI/ML 开源项目与模型动态，生成一份高质量的「AI 晨报雷达」。

【输入数据】
{items_json}

【处理要求】
1. 从列表中挑选出最具代表性、实用价值最高、值得关注的 6-8 个项目。
2. 将入选项目严格归为以下 4 大分类之一：
   - 🤖 [Agent & 自动化流]：自主智能体、多 Agent 协同、工作流、Skill 插件
   - ⚡ [模型 & 推理革命]：端侧小模型、最新微调权重、极速推理优化
   - 🛠️ [开发者神器 & 效率]：代码辅助、UI 动效、图表设计与数据处理
   - 🔓 [前沿黑客 & 逆向探索]：反爬对抗、协议逆向、系统级越狱或底层探索
3. 对每个项目输出：
   - category: 上述 4 大分类之一
   - title: 项目名称（保持可读）
   - url: 原文链接
   - metric: 热度指标（如 ⭐ 2051 或 🤗 1024）
   - tag: 保留输入的 "🆕 新上榜" 或 "🔥 持续霸榜"
   - summary: 一句话痛点直击（说明它解决了什么痛点，为什么今天爆火，40字以内精炼中文）
   - target_audience: 适合人群（如：前端工程师、全栈开发者、AI 创作者、独立开发者、安全团队）
   - stars: 推荐指数，格式为 ⭐⭐⭐⭐⭐（3 到 5 颗星）
4. 返回格式必须为纯 JSON 数组，无需包裹任何 markdown 标记。
"""

def analyze_with_gemini(items: List[Dict[str, Any]], api_key: str, model_name: str = DEFAULT_MODEL) -> List[Dict[str, Any]]:
    """
    调用 Google Gemini Flash API 进行结构化智能提炼
    """
    if not api_key:
        print("[Analyzer] 未检测到 GEMINI_API_KEY，启用降级纯文本规则提炼")
        return fallback_analysis(items)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    prompt = PROMPT_TEMPLATE.format(items_json=json.dumps(items, ensure_ascii=False, indent=2))

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            # 解析 Gemini 返回文本
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("Gemini 未返回候选内容")
                
            raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
            parsed = json.loads(raw_text)
            if isinstance(parsed, list):
                print(f"[Analyzer] Gemini 成功精炼出 {len(parsed)} 条深度动态")
                return parsed
            elif isinstance(parsed, dict) and "items" in parsed:
                return parsed["items"]
            else:
                return fallback_analysis(items)
    except Exception as e:
        print(f"[Analyzer] 调用 Gemini API 出错 ({e})，将启用本地降级逻辑")
        return fallback_analysis(items)


def fallback_analysis(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    降级处理：当未配置 API Key 或网络故障时，保证晨报不中断
    """
    fallback_items = []
    for it in items[:6]:
        category = "🛠️ [开发者神器 & 效率]"
        if "agent" in it["title"].lower() or "skill" in it["title"].lower():
            category = "🤖 [Agent & 自动化流]"
        elif it["source"] == "HuggingFace":
            category = "⚡ [模型 & 推理革命]"
        elif "turnstile" in it["title"].lower() or "bypass" in it["title"].lower():
            category = "🔓 [前沿黑客 & 逆向探索]"

        summary = it["raw_description"] if it["raw_description"] else "过去 24 小时热度快速飙升的 AI 项目。"
        if len(summary) > 60:
            summary = summary[:57] + "..."

        fallback_items.append({
            "category": category,
            "title": it["title"],
            "url": it["url"],
            "metric": it["metric"],
            "tag": it.get("tag", "🆕 新上榜"),
            "summary": summary,
            "target_audience": "开发者与技术极客",
            "stars": "⭐⭐⭐⭐"
        })
    return fallback_items
