import unittest
from unittest.mock import patch

from src.deduplicator import filter_and_mark_items


class DeduplicatorTest(unittest.TestCase):
    def test_higher_priority_is_selected_first(self):
        items = [
            {"url": "https://example.com/model", "title": "普通模型", "metric": "", "rank": 1, "priority": 100},
            {"url": "https://example.com/hot", "title": "AI 热点", "metric": "", "rank": 2, "priority": 400},
            {"url": "https://example.com/open", "title": "开源项目", "metric": "", "rank": 3, "priority": 300},
            {"url": "https://example.com/voice", "title": "语音模型", "metric": "", "rank": 4, "priority": 200},
        ]

        with patch("src.deduplicator.load_history", return_value={"items": {}}):
            selected, _ = filter_and_mark_items(items, max_push=4)

        self.assertEqual(
            [item["title"] for item in selected],
            ["AI 热点", "开源项目", "语音模型", "普通模型"],
        )


if __name__ == "__main__":
    unittest.main()
