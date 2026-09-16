import os
import json
import httpx
from typing import List, Dict, Any

OPENAI_DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-6-astra")
GEMINI_DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

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
   - summary: 必须独立生成一条 40 字以内的自然中文总结。结合 title、raw_description、来源与热度，说明项目/新闻在做什么，以及为什么值得关注；不得照抄标题、英文简介或输出英文句子，不得凭空补充输入中没有的事实。专有名词可保留英文。
   - target_audience: 适合人群（如：前端工程师、全栈开发者、AI 创作者、独立开发者、安全团队）
   - stars: 推荐指数，格式为 ⭐⭐⭐⭐⭐（3 到 5 颗星）
5. 返回格式必须为纯 JSON 数组，无需包裹任何 markdown 标记。
"""

def parse_analysis_response(raw_text: str) -> List[Dict[str, Any]]:
    """解析模型返回的 JSON 数组或 {"items": [...]} 结构。"""
    parsed = json.loads(raw_text)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
        return parsed["items"]
    raise ValueError("模型返回的 JSON 不包含资讯列表")


def analyze_with_openai(
    items: List[Dict[str, Any]], api_key: str, model_name: str = OPENAI_DEFAULT_MODEL
) -> List[Dict[str, Any]]:
    """调用 OpenAI Responses API；失败交由调用方切换 Gemini。"""
    if not api_key:
        raise ValueError("未配置 OPENAI_API_KEY")

    prompt = PROMPT_TEMPLATE.format(items_json=json.dumps(items, ensure_ascii=False, indent=2))
    payload = {
        "model": model_name,
        "input": prompt,
        "text": {"format": {"type": "json_object"}},
    }

    with httpx.Client(timeout=45.0) as client:
        resp = client.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    raw_text = data.get("output_text", "").strip()
    if not raw_text:
        raise ValueError("OpenAI 未返回文本内容")
    result = parse_analysis_response(raw_text)
    print(f"[Analyzer] OpenAI ({model_name}) 成功精炼出 {len(result)} 条深度动态")
    return result


def analyze_with_gemini(
    items: List[Dict[str, Any]], api_key: str, model_name: str = GEMINI_DEFAULT_MODEL
) -> List[Dict[str, Any]]:
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
            result = parse_analysis_response(raw_text)
            print(f"[Analyzer] Gemini 成功精炼出 {len(result)} 条深度动态")
            return result
    except Exception as e:
        print(f"[Analyzer] 调用 Gemini API 出错 ({e})，将启用本地降级逻辑")
        return fallback_analysis(items)


def analyze_items(
    items: List[Dict[str, Any]],
    openai_api_key: str,
    openai_model: str = OPENAI_DEFAULT_MODEL,
    gemini_api_key: str = "",
    gemini_model: str = GEMINI_DEFAULT_MODEL,
) -> List[Dict[str, Any]]:
    """按 OpenAI → Gemini → 本地规则的顺序生成晨报。"""
    if openai_api_key:
        try:
            return analyze_with_openai(items, openai_api_key, openai_model)
        except Exception as error:
            print(f"[Analyzer] OpenAI 调用失败 ({error})，切换 Gemini 兜底")
    else:
        print("[Analyzer] 未检测到 OPENAI_API_KEY，切换 Gemini 兜底")

    if gemini_api_key:
        return analyze_with_gemini(items, gemini_api_key, gemini_model)

    print("[Analyzer] 未检测到 GEMINI_API_KEY，启用降级纯文本规则提炼")
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

        summary = fallback_summary(it)

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


def fallback_summary(item: Dict[str, Any]) -> str:
    """未配置 Gemini 时，仍提供不含英文原文的中文一句话说明。"""
    title = item["title"]
    source_type = item.get("source_type")
    if source_type == "github_high_star":
        return f"「{title}」是总 Star 达标且近期活跃的 AI 开源项目，值得关注其最新工程进展。"
    if source_type == "sopilot":
        return f"围绕「{title}」的高热 AI 社媒讨论，反映当日市场关注焦点。"
    if source_type == "aihot":
        return f"「{title}」登上 AI 热点榜，代表当日值得跟进的技术或产品进展。"
    return f"「{title}」是今日入选的 {item.get('source_category', '科技')} 动态，建议结合原文评估价值。"
