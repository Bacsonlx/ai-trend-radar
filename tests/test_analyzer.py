import unittest
from unittest.mock import patch

from src.analyzer import analyze_items, fallback_analysis, parse_analysis_response


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

    def test_openai_failure_falls_back_to_gemini(self):
        expected = [{"title": "Gemini fallback"}]
        with patch("src.analyzer.analyze_with_openai", side_effect=RuntimeError("network error")) as openai, \
             patch("src.analyzer.analyze_with_gemini", return_value=expected) as gemini:
            result = analyze_items(
                [{"title": "item"}],
                openai_api_key="openai-key",
                gemini_api_key="gemini-key",
            )

        self.assertEqual(result, expected)
        openai.assert_called_once()
        gemini.assert_called_once()

    def test_parse_analysis_response_accepts_items_wrapper(self):
        self.assertEqual(
            parse_analysis_response('{"items": [{"title": "热点"}]}'),
            [{"title": "热点"}],
        )


if __name__ == "__main__":
    unittest.main()
