import unittest


from agent.llm.apply_planner import _extract_json


class TestExtractJson(unittest.TestCase):
    def test_extracts_plain_json(self):
        data = _extract_json('{"a": 1, "b": "x"}')
        self.assertEqual(data["a"], 1)
        self.assertEqual(data["b"], "x")

    def test_extracts_from_fenced(self):
        s = "```json\n{\"field_values\": {\"#x\": \"y\"}, \"uploads\": {}, \"notes\": []}\n```"
        data = _extract_json(s)
        self.assertIn("field_values", data)

    def test_extracts_from_extra_text(self):
        s = "Here you go:\\n{\\n  \"k\": \"v\"\\n}\\nThanks"
        data = _extract_json(s)
        self.assertEqual(data["k"], "v")


if __name__ == "__main__":
    unittest.main()

