import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setup import slugify


class TestSlugify(unittest.TestCase):
    def test_simple_phrase(self):
        self.assertEqual(slugify("Build login flow"), "build-login-flow")

    def test_strips_punctuation(self):
        self.assertEqual(slugify("Build the login flow!!!"), "build-the-login-flow")

    def test_collapses_whitespace(self):
        self.assertEqual(slugify("Build   the   flow"), "build-the-flow")

    def test_truncates_to_40_chars(self):
        long_input = "a " * 50
        result = slugify(long_input)
        self.assertLessEqual(len(result), 40)

    def test_no_trailing_hyphen_on_truncation(self):
        result = slugify("abcdefghij " * 10)
        self.assertFalse(result.endswith("-"))
        self.assertLessEqual(len(result), 40)

    def test_handles_unicode_by_dropping(self):
        self.assertEqual(slugify("café résumé"), "caf-rsum")

    def test_empty_input_returns_sprint(self):
        self.assertEqual(slugify(""), "sprint")

    def test_all_punctuation_returns_sprint(self):
        self.assertEqual(slugify("!!!???"), "sprint")


if __name__ == "__main__":
    unittest.main()
