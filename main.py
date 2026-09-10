import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

from src.fetcher import fetch_hype_items
from src.deduplicator import filter_and_mark_items, save_history
from src.analyzer import analyze_with_gemini
from src.feishu import send_feishu_card

def main():
    # 优先加载本地 .env 文件
    load_dotenv()

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
    feishu_webhook = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
    feishu_secret = os.getenv("FEISHU_SECRET", "").strip()

    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"=== 🚀 开始执行「AI 趋势雷达」晨报任务 ({today_str}) ===")

    # 1. 抓取数据
    print("[1/4] 正在抓取 hype.replicate.dev 过去 24 小时榜单...")
    try:
        raw_items = fetch_hype_items(limit=15)
    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        sys.exit(1)

    # 2. 历史对比与去重
    print("[2/4] 正在比对历史缓存，识别全新黑马与霸榜项目...")
    filtered_items, updated_history = filter_and_mark_items(raw_items, max_push=10)

    # 3. Gemini 智能研判
    print(f"[3/4] 正在调用 Gemini Flash ({gemini_model}) 进行痛点提炼与分类...")
    analyzed_items = analyze_with_gemini(filtered_items, api_key=gemini_key, model_name=gemini_model)

    # 4. 推送到飞书
    print("[4/4] 正在推送至飞书群机器人...")
    if feishu_webhook:
        success = send_feishu_card(
            webhook_url=feishu_webhook,
            items=analyzed_items,
            date_str=today_str,
            secret=feishu_secret if feishu_secret else None
        )
        if success:
            # 仅在推送成功后持久化更新历史记录
            save_history(updated_history)
            print("✅ 历史缓存已持久化更新！")
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
