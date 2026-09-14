import unittest
from unittest.mock import patch

from src.fetcher import (
    assign_priorities,
    fetch_all_sources,
    fetch_horizon_items,
    parse_aihot_items,
    parse_horizon_items,
)


class FetcherTest(unittest.TestCase):
    def setUp(self):
        self.aihot_source = {
            "name": "AIHot",
            "type": "aihot",
            "category": "AI 热点",
            "url": "https://aihot.news/",
            "limit": 10,
        }

    def test_aihot_parser_extracts_title_link_and_heat(self):
        html = """
        <ol><li><a href="/story/abc">新模型发布</a><span>321 热度</span></li></ol>
        """

        items = parse_aihot_items(html, self.aihot_source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "新模型发布")
        self.assertEqual(items[0]["url"], "https://aihot.news/story/abc")
        self.assertEqual(items[0]["metric"], "🔥 321 热度")

    def test_horizon_parser_extracts_article_and_summary(self):
        source = {
            "name": "Horizon",
            "type": "horizon",
            "category": "高质量技术速递",
            "url": "https://example.com/{date}",
            "limit": 10,
        }
        html = """
        <h2>科技新闻</h2>
        <h3><a href="https://example.com/story">AI 芯片发布</a> ⭐️ 8.5/10</h3>
        <p>新芯片显著降低推理能耗。</p><hr>
        """

        items = parse_horizon_items(html, source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source"], "Horizon · 科技新闻")
        self.assertEqual(items[0]["metric"], "⭐ 8.5/10")
        self.assertEqual(items[0]["raw_description"], "新芯片显著降低推理能耗。")

    def test_horizon_date_is_converted_to_path_format(self):
        source = {
            "name": "Horizon",
            "type": "horizon",
            "url": "https://example.com/{date}/summary-zh.html",
        }
        with patch("src.fetcher.request_html", return_value="") as request_html:
            fetch_horizon_items(source, "2026-09-09")

        request_html.assert_called_once_with(
            "https://example.com/2026/09/09/summary-zh.html", timeout=15.0
        )

    def test_single_source_failure_does_not_discard_other_results(self):
        sources = [
            {"name": "成功源", "type": "aihot"},
            {"name": "失败源", "type": "horizon"},
        ]

        def fake_fetch(source, _report_date):
            if source["name"] == "失败源":
                raise RuntimeError("请求超时")
            return [{"title": "可用资讯"}]

        with patch("src.fetcher.fetch_source", side_effect=fake_fetch):
            items = fetch_all_sources("2026-09-09", sources)

        self.assertEqual([item["title"] for item in items], ["可用资讯"])

    def test_priorities_follow_requested_order(self):
        items = [
            {"source_type": "hype", "source": "HuggingFace", "title": "通用模型"},
            {"source_type": "hype", "source": "HuggingFace", "title": "语音识别模型"},
            {"source_type": "hype", "source": "GitHub", "title": "开源项目"},
            {"source_type": "aihot", "source": "AIHot", "title": "AI 热点"},
        ]

        assign_priorities(items, {"ai_hot": 400, "open_source": 300, "voice_model": 200, "other_model": 100})

        self.assertEqual([item["priority"] for item in items], [100, 200, 300, 400])


if __name__ == "__main__":
    unittest.main()
