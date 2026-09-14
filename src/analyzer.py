import os
import json
import httpx
from typing import List, Dict, Any

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

PROMPT_TEMPLATE = """你是一名资深 AI 架构师兼前沿技术观察员。
请根据以下过去 24 小时聚合的 AI、硬件与极客热点，生成一份高质量、信息密度高的「AI 晨报雷达」。

【输入数据】
{items_json}

【处理要求】
1. 从列表中仅挑选 8-10 条最具代表性、事实明确、影响面大或实用价值高的资讯；同一事件的重复报道只能保留一条。忽略营销软文、泛泛观点、低热度重复信息与缺少具体事实的内容。
2. 输入包含 priority 与 priority_label，代表用户指定的优先级：AI 热点 > 开源项目 > 语音模型 > 其他模型。优先选择高优先级内容，并严格按 priority 从高到低输出。
3. 将入选资讯严格归为以下 5 类之一：
   - 🧠 [AI 模型 & 研究]：基础模型、推理、论文、AI 科研突破
   - 🤖 [AI 产品 & 智能体]：Agent、AI 产品、工作流、应用落地
   - ⚙️ [开发者 & 开源]：GitHub、工具链、框架、工程效率
   - 🖥️ [硬件 & 算力]：芯片、机器人、终端设备、数据中心与基础设施
   - 🌐 [科技产业 & 极客]：重要公司、产业政策、商业趋势与深度科技观察
4. 对每个项目输出：
   - category: 上述 5 大分类之一
   - title: 项目名称（保持可读）
   - url: 原文链接
   - metric: 热度指标（如 ⭐ 2051 或 🤗 1024）
   - tag: 保留输入的 "🆕 新上榜" 或 "🔥 持续霸榜"
   - source: 保留输入来源名称
   - summary: 一句话说明（概括这条新闻/项目主要讲什么、解决什么问题或影响什么，40字以内精炼中文；不得泛泛而谈）
   - target_audience: 适合人群（如：前端工程师、全栈开发者、AI 创作者、独立开发者、安全团队）
   - stars: 推荐指数，格式为 ⭐⭐⭐⭐⭐（3 到 5 颗星）
5. 返回格式必须为纯 JSON 数组，无需包裹任何 markdown 标记。
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
    for it in items[:10]:
        title_lower = it["title"].lower()
        category = "⚙️ [开发者 & 开源]"
        if any(word in title_lower for word in ("agent", "智能体", "助手", "workflow")):
            category = "🤖 [AI 产品 & 智能体]"
        elif any(word in title_lower for word in ("model", "模型", "论文", "推理", "deepseek", "openai")):
            category = "🧠 [AI 模型 & 研究]"
        elif any(word in title_lower for word in ("芯片", "gpu", "机器人", "硬件", "算力", "cuda")):
            category = "🖥️ [硬件 & 算力]"
        elif it.get("source_type") in {"geekpark", "horizon"}:
            category = "🌐 [科技产业 & 极客]"

        summary = it["raw_description"] if it["raw_description"] else "过去 24 小时热度快速飙升的 AI 项目。"
        if len(summary) > 60:
            summary = summary[:57] + "..."

        fallback_items.append({
            "category": category,
            "title": it["title"],
            "url": it["url"],
            "metric": it["metric"],
            "tag": it.get("tag", "🆕 新上榜"),
            "source": it.get("source", ""),
            "summary": summary,
            "target_audience": "开发者与技术极客",
            "stars": "⭐⭐⭐⭐"
        })
    return fallback_items
