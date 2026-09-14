import unittest

from src.analyzer import fallback_analysis


class AnalyzerTest(unittest.TestCase):
    def test_fallback_summary_does_not_copy_english_description(self):
        items = [{
            "title": "org/high-star",
            "url": "https://github.com/org/high-star",
            "metric": "⭐ 2,000",
            "source": "GitHub 高星活跃项目",
            "source_type": "github_high_star",
            "raw_description": "An English description that must not appear in the card.",
        }]

        result = fallback_analysis(items)

        self.assertIn("总 Star 达标", result[0]["summary"])
        self.assertNotIn("An English description", result[0]["summary"])


if __name__ == "__main__":
    unittest.main()
