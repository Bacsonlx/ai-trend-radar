import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SOURCES_FILE = ROOT_DIR / "config" / "sources.json"
DEFAULT_PRIORITY_WEIGHTS = {
    "ai_hot": 400,
    "open_source": 300,
    "voice_model": 200,
    "other_model": 100,
}
VOICE_MODEL_KEYWORDS = (
    "speech", "voice", "audio", "tts", "asr", "stt", "whisper",
    "语音", "音频", "文本转语音", "语音识别",
)
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}


def load_sources(config_path: Path | None = None) -> List[Dict[str, Any]]:
    """读取可配置的信息源，只返回已启用的来源。"""
    source_file = config_path or DEFAULT_SOURCES_FILE
    with source_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    sources = data.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("sources.json 中的 sources 必须是数组")
    return [source for source in sources if source.get("enabled", True)]


def load_priority_weights(config_path: Path | None = None) -> Dict[str, int]:
    """读取资讯优先级权重，缺失项使用默认值。"""
    source_file = config_path or DEFAULT_SOURCES_FILE
    with source_file.open("r", encoding="utf-8") as file:
        configured_weights = json.load(file).get("priority_weights", {})
    return {
        name: int(configured_weights.get(name, default))
        for name, default in DEFAULT_PRIORITY_WEIGHTS.items()
    }


def fetch_all_sources(
    report_date: str,
    sources: Iterable[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """并发抓取所有来源；任意单一来源失败都不会中断晨报。"""
    active_sources = list(sources) if sources is not None else load_sources()
    priority_weights = DEFAULT_PRIORITY_WEIGHTS if sources is not None else load_priority_weights()
    if not active_sources:
        return []

    items: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=len(active_sources)) as executor:
        futures = {
            executor.submit(fetch_source, source, report_date): source
            for source in active_sources
        }
        for future in as_completed(futures):
            source = futures[future]
            source_name = source.get("name", source.get("type", "未知来源"))
            try:
                source_items = future.result()
                items.extend(assign_priorities(source_items, priority_weights))
                print(f"[Fetcher] {source_name} 抓取到 {len(source_items)} 条")
            except Exception as error:
                print(f"[Fetcher] {source_name} 抓取失败，已跳过: {error}")

    return items


def assign_priorities(
    items: List[Dict[str, Any]],
    weights: Dict[str, int],
) -> List[Dict[str, Any]]:
    """按 AI 热点、开源、语音模型、其他模型标记优先级。"""
    for item in items:
        priority_key = "other_model"
        if item.get("source_type") == "aihot":
            priority_key = "ai_hot"
        elif item.get("source") == "GitHub":
            priority_key = "open_source"
        elif is_voice_model(item):
            priority_key = "voice_model"
        item["priority"] = weights[priority_key]
        item["priority_label"] = {
            "ai_hot": "AI 热点",
            "open_source": "开源项目",
            "voice_model": "语音模型",
            "other_model": "其他模型",
        }[priority_key]
    return items


def is_voice_model(item: Dict[str, Any]) -> bool:
    text = f"{item.get('title', '')} {item.get('raw_description', '')}".lower()
    return any(keyword in text for keyword in VOICE_MODEL_KEYWORDS)


def fetch_source(source: Dict[str, Any], report_date: str) -> List[Dict[str, Any]]:
    """按来源类型分发抓取器。"""
    source_type = source.get("type")
    if source_type == "hype":
        return fetch_hype_items(source)
    if source_type == "aihot":
        return fetch_aihot_items(source)
    if source_type == "geekpark":
        return fetch_geekpark_items(source)
    if source_type == "horizon":
        return fetch_horizon_items(source, report_date)
    raise ValueError(f"不支持的信息源类型: {source_type}")


def fetch_hype_items(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    """抓取 Hype 过去 24 小时的开源与模型热度榜。"""
    html = request_html(source["url"], timeout=source.get("timeout", 15.0), retries=1)
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []

    for rank, li in enumerate(soup.select("ul li")[:source.get("limit", 15)], start=1):
        link = li.select_one("a[target='_blank']")
        if not link:
            continue

        url = link.get("href", "").strip()
        title = link.get_text(" ", strip=True)
        if not url or not title:
            continue

        source_name = "Hype"
        if "github.com" in url:
            source_name = "GitHub"
        elif "huggingface.co" in url:
            source_name = "HuggingFace"
        elif "reddit.com" in url:
            source_name = "Reddit"
        elif "replicate.com" in url:
            source_name = "Replicate"

        metric_el = li.select_one("div > div > span, span.ml-1")
        desc_el = li.select_one("p")
        items.append(build_item(
            source,
            rank=rank,
            title=title,
            url=url,
            metric=metric_el.get_text(" ", strip=True) if metric_el else "",
            description=desc_el.get_text(" ", strip=True) if desc_el else "",
            source_name=source_name,
        ))
    return items


def fetch_aihot_items(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    """抓取 AIHot 首页的实时热点榜。"""
    html = request_html(source["url"], timeout=source.get("timeout", 15.0))
    return parse_aihot_items(html, source)


def parse_aihot_items(html: str, source: Dict[str, Any]) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []
    seen_urls = set()
    for link in soup.select("a[href^='/story/']"):
        if len(items) >= source.get("limit", 10):
            break
        url = urljoin(source["url"], link.get("href", ""))
        title = link.get_text(" ", strip=True)
        if not title or url in seen_urls:
            continue
        seen_urls.add(url)

        row_text = link.parent.get_text(" ", strip=True) if link.parent else ""
        metric_match = re.search(r"([\d,]+)\s*热度", row_text)
        items.append(build_item(
            source,
            rank=len(items) + 1,
            title=title,
            url=url,
            metric=f"🔥 {metric_match.group(1)} 热度" if metric_match else "",
            description="",
        ))
    return items


def fetch_geekpark_items(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    """抓取极客公园首页的新闻链接；站点反爬时由上层自动跳过。"""
    html = request_html(source["url"], timeout=source.get("timeout", 15.0))
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []
    seen_urls = set()
    for link in soup.select("a[href*='/news/']"):
        if len(items) >= source.get("limit", 10):
            break
        url = urljoin(source["url"], link.get("href", ""))
        title = link.get_text(" ", strip=True)
        if not title or url in seen_urls:
            continue
        seen_urls.add(url)
        container = link.find_parent(["article", "li", "div"])
        description = ""
        if container:
            paragraph = container.find("p")
            description = paragraph.get_text(" ", strip=True) if paragraph else ""
        items.append(build_item(
            source,
            rank=len(items) + 1,
            title=title,
            url=url,
            metric="",
            description=description,
        ))
    return items


def fetch_horizon_items(source: Dict[str, Any], report_date: str) -> List[Dict[str, Any]]:
    """抓取 Horizon 指定日期的中文高分技术速递。"""
    url = source["url"].format(date=report_date.replace("-", "/"))
    html = request_html(url, timeout=source.get("timeout", 15.0))
    return parse_horizon_items(html, source)


def parse_horizon_items(html: str, source: Dict[str, Any]) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []
    section = "技术资讯"
    for heading in soup.select("h2, h3"):
        if heading.name == "h2":
            section = heading.get_text(" ", strip=True)
            continue
        if len(items) >= source.get("limit", 10):
            break
        link = heading.select_one("a[href^='http']")
        if not link:
            continue
        title = link.get_text(" ", strip=True)
        url = link.get("href", "").strip()
        if not title or not url:
            continue
        heading_text = heading.get_text(" ", strip=True)
        score = re.search(r"⭐️?\s*([\d.]+/10)", heading_text)
        description = sibling_text_until_break(heading)
        items.append(build_item(
            source,
            rank=len(items) + 1,
            title=title,
            url=url,
            metric=f"⭐ {score.group(1)}" if score else "",
            description=description,
            source_name=f"Horizon · {section}",
        ))
    return items


def sibling_text_until_break(heading: Any) -> str:
    parts = []
    for sibling in heading.next_siblings:
        name = getattr(sibling, "name", None)
        if name in {"h2", "h3", "hr"}:
            break
        if name == "p":
            text = sibling.get_text(" ", strip=True)
            if text:
                parts.append(text)
    return " ".join(parts)[:600]


def request_html(url: str, timeout: float, retries: int = 0) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(url, headers=DEFAULT_HEADERS)
                response.raise_for_status()
                return response.text
        except Exception as error:
            last_error = error
            if attempt < retries:
                time.sleep(attempt + 1)
    raise RuntimeError(f"请求 {url} 失败: {last_error}")


def build_item(
    source: Dict[str, Any],
    rank: int,
    title: str,
    url: str,
    metric: str,
    description: str,
    source_name: str | None = None,
) -> Dict[str, Any]:
    return {
        "rank": rank,
        "source": source_name or source["name"],
        "source_type": source["type"],
        "source_category": source.get("category", "科技资讯"),
        "title": title,
        "url": url,
        "metric": metric,
        "raw_description": description,
    }
