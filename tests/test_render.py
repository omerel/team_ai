import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setup import render_template, RenderError


class TestRenderTemplate(unittest.TestCase):
    def test_simple_substitution(self):
        out = render_template("hello $name", {"name": "rocky"})
        self.assertEqual(out, "hello rocky")

    def test_multiple_vars(self):
        out = render_template(
            "$nickname is the $role",
            {"nickname": "rocky", "role": "backend"},
        )
        self.assertEqual(out, "rocky is the backend")

    def test_braced_variable(self):
        out = render_template("${nickname}_log", {"nickname": "rocky"})
        self.assertEqual(out, "rocky_log")

    def test_dollar_escape(self):
        out = render_template("price is $$5", {})
        self.assertEqual(out, "price is $5")

    def test_missing_variable_raises(self):
        with self.assertRaises(RenderError):
            render_template("hello $name", {})

    def test_extra_vars_ignored(self):
        out = render_template("hello $name", {"name": "x", "extra": "y"})
        self.assertEqual(out, "hello x")


if __name__ == "__main__":
    unittest.main()
