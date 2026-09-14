import unittest
from unittest.mock import patch

from src.fetcher import (
    assign_priorities,
    fetch_all_sources,
    parse_github_high_star_items,
    fetch_horizon_items,
    parse_aihot_items,
    parse_horizon_items,
    parse_sopilot_items,
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

    def test_sopilot_parser_only_keeps_ai_topics(self):
        source = {
            "name": "SoPilot",
            "type": "sopilot",
            "category": "AI 社媒热点",
            "url": "https://sopilot.net/zh",
            "limit": 5,
        }
        html = """
        <section><h3>起爆热点话题</h3>
          <article><div><a href="/rank/topic/ai">GPT 模型能力讨论</a><div><span>9 帖</span><span>27万</span></div></div></article>
          <article><div><a href="/rank/topic/other">足球比赛结果</a><div><span>8 帖</span><span>31万</span></div></div></article>
        </section>
        """

        items = parse_sopilot_items(html, source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "GPT 模型能力讨论")
        self.assertEqual(items[0]["metric"], "🔥 27万 曝光")

    def test_github_high_star_parser_filters_repositories_below_threshold(self):
        source = {"name": "GitHub 高星活跃项目", "type": "github_high_star", "min_stars": 2000, "limit": 5}
        data = {
            "items": [
                {"full_name": "org/high-star", "html_url": "https://github.com/org/high-star", "stargazers_count": 2000, "description": "AI project"},
                {"full_name": "org/low-star", "html_url": "https://github.com/org/low-star", "stargazers_count": 1999, "description": "AI project"},
            ]
        }

        items = parse_github_high_star_items(data, source)

        self.assertEqual([item["title"] for item in items], ["org/high-star"])
        self.assertEqual(items[0]["metric"], "⭐ 2,000")

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
            {"source_type": "github_high_star", "source": "GitHub 高星活跃项目", "title": "开源项目"},
            {"source_type": "aihot", "source": "AIHot", "title": "AI 热点"},
        ]

        assign_priorities(items, {"ai_hot": 400, "open_source": 300, "voice_model": 200, "other_model": 100})

        self.assertEqual([item["priority"] for item in items], [100, 200, 300, 400])


if __name__ == "__main__":
    unittest.main()
