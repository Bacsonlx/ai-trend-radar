import time
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any

HYPE_URL = "https://hype.replicate.dev/?filter=past_day&sources=GitHub,HuggingFace,Reddit,Replicate"

def fetch_hype_items(limit: int = 15, max_retries: int = 3) -> List[Dict[str, Any]]:
    """
    抓取 hype.replicate.dev 过去 24 小时榜单数据
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
    }

    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                resp = client.get(HYPE_URL, headers=headers)
                resp.raise_for_status()
                html = resp.text
                break
        except Exception as e:
            last_err = e
            print(f"[Fetcher] 抓取失败 (尝试 {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(2 * attempt)
    else:
        raise RuntimeError(f"未能成功从 {HYPE_URL} 获取数据: {last_err}")

    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []

    list_elements = soup.select("ul li")
    for idx, li in enumerate(list_elements[:limit], start=1):
        link_el = li.select_one("a[target='_blank']")
        if not link_el:
            continue

        title = link_el.get_text(strip=True)
        url = link_el.get("href", "").strip()

        # 提取指标（如 ⭐ 2051 或 🤗 1024，排除前面的排名序号 span）
        metric_el = li.select_one("div > div > span, span.ml-1")
        metric = metric_el.get_text(strip=True) if metric_el else ""

        # 提取简介
        desc_el = li.select_one("p")
        raw_desc = desc_el.get_text(strip=True) if desc_el else ""

        # 识别来源平台
        source = "Other"
        if "github.com" in url:
            source = "GitHub"
        elif "huggingface.co" in url:
            source = "HuggingFace"
        elif "reddit.com" in url:
            source = "Reddit"
        elif "replicate.com" in url:
            source = "Replicate"

        items.append({
            "rank": idx,
            "source": source,
            "title": title,
            "url": url,
            "metric": metric,
            "raw_description": raw_desc
        })

    print(f"[Fetcher] 成功解析到 {len(items)} 条热门项目")
    return items


if __name__ == "__main__":
    results = fetch_hype_items(5)
    for r in results:
        print(r)
