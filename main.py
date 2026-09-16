import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from src.fetcher import fetch_all_sources
from src.deduplicator import filter_and_mark_items, save_history
from src.analyzer import analyze_items
from src.feishu import send_feishu_card

REPORT_TIMEZONE = ZoneInfo("Asia/Taipei")


def get_report_date(now: datetime | None = None) -> str:
    """返回台北时区的昨日日期。"""
    current_time = now or datetime.now(REPORT_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=REPORT_TIMEZONE)
    else:
        current_time = current_time.astimezone(REPORT_TIMEZONE)
    return (current_time.date() - timedelta(days=1)).isoformat()


def main():
    # 优先加载本地 .env 文件
    load_dotenv()

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model = os.getenv("OPENAI_MODEL", "gpt-6-astra").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    feishu_webhook = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
    feishu_secret = os.getenv("FEISHU_SECRET", "").strip()

    report_date = get_report_date()
    print(f"=== 🚀 开始执行「AI 趋势雷达」昨日晨报任务 ({report_date}) ===")

    # 1. 抓取数据
    print("[1/4] 正在并发抓取 AI、硬件与极客热点来源...")
    raw_items = fetch_all_sources(report_date)
    if not raw_items:
        print("❌ 所有信息源均未返回内容，任务终止。")
        sys.exit(1)

    # 2. 历史对比与去重
    print("[2/4] 正在比对历史缓存，识别全新黑马与霸榜项目...")
    filtered_items, updated_history = filter_and_mark_items(raw_items, max_push=30)

    # 3. OpenAI 智能研判，Gemini 仅在主模型失败时兜底
    print(f"[3/4] 正在调用 OpenAI ({openai_model}) 进行热点提炼与分类...")
    analyzed_items = analyze_items(
        filtered_items,
        openai_api_key=openai_key,
        openai_model=openai_model,
        gemini_api_key=gemini_key,
        gemini_model=gemini_model,
    )

    # 4. 推送到飞书
    print("[4/4] 正在推送至飞书群机器人...")
    if feishu_webhook:
        success = send_feishu_card(
            webhook_url=feishu_webhook,
            items=analyzed_items,
            date_str=report_date,
            secret=feishu_secret if feishu_secret else None
        )
        if success:
            # 仅在推送成功后持久化更新历史记录
            save_history(updated_history)
            print("✅ 历史缓存已持久化更新！")
        else:
            print("❌ 飞书推送失败，任务终止且不更新历史缓存。")
            sys.exit(1)
    else:
        print("\n⚠️ 未配置 FEISHU_WEBHOOK_URL，以下为控制台预览：")
        print("-" * 50)
        for item in analyzed_items:
            print(f"【{item['category']}】{item.get('tag', '')} {item['title']} ({item['metric']})")
            print(f"  🔗 链接: {item['url']}")
            print(f"  💡 痛点: {item['summary']}")
            print(f"  🎯 适合: {item['target_audience']} | 评级: {item['stars']}")
            print()
        print("-" * 50)
        # 本地测试预览也更新历史
        save_history(updated_history)

    print("🎉 任务执行完毕！")

if __name__ == "__main__":
    main()
