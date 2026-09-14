import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "history.json")

def load_history() -> Dict[str, Any]:
    if not os.path.exists(CACHE_FILE):
        return {"items": {}}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Deduplicator] 读取历史缓存失败，将重新初始化: {e}")
        return {"items": {}}

def save_history(history: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    # 保留最近 300 条记录防止文件膨胀
    items = history.get("items", {})
    if len(items) > 300:
        # 按最后看见时间排序保留
        sorted_keys = sorted(
            items.keys(),
            key=lambda k: items[k].get("last_seen", ""),
            reverse=True
        )[:300]
        history["items"] = {k: items[k] for k in sorted_keys}

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def filter_and_mark_items(items: List[Dict[str, Any]], max_push: int = 10) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    对比历史记录：
    - 如果是全新项目，标记 is_new = True
    - 如果是近期已经推送过的项目，标记 is_repeat = True
    - 返回推荐推送的项目列表，以及更新后的 history 字典
    """
    history = load_history()
    seen = history.setdefault("items", {})
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    fresh_items = []
    for it in items:
        url = it["url"]
        if url not in seen:
            it["is_new"] = True
            it["tag"] = "🆕 新上榜"
            fresh_items.append(it)
            seen[url] = {
                "title": it["title"],
                "first_seen": today_str,
                "last_seen": today_str,
                "metric": it["metric"],
                "pushed_count": 1
            }
        else:
            rec = seen[url]
            rec["last_seen"] = today_str
            rec["metric"] = it["metric"]
            rec["pushed_count"] = rec.get("pushed_count", 0) + 1
            it["is_new"] = False
            it["tag"] = "🔥 持续霸榜"
            # 持续霸榜的项目也允许入选，但优先保证新项目
            fresh_items.append(it)

    # 先按资讯优先级，再优先选新项目，最后按来源内热度排名。
    sorted_items = sorted(
        fresh_items,
        key=lambda x: (-x.get("priority", 0), not x["is_new"], x["rank"]),
    )
    return sorted_items[:max_push], history
