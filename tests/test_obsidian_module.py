import unittest
import tempfile
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setup import scaffold_project


class TestObsidianDisabledDefault(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = self.tmp / "proj"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_disabled_leaves_no_obsidian_placeholders(self):
        scaffold_project(self.target, minimal=True, force=False)
        for path in self.target.rglob("*"):
            if path.is_file() and path.suffix in (".md", ".json"):
                text = path.read_text(errors="ignore")
                self.assertNotIn("$obsidian_", text, f"leftover placeholder in {path}")

    def test_disabled_creates_no_obsidian_artifacts(self):
        scaffold_project(self.target, minimal=True, force=False)
        self.assertFalse((self.target / "wiki").exists(), "wiki/ must not exist when disabled")
        self.assertFalse((self.target / ".claude" / "skills" / "wiki").exists())
        self.assertFalse((self.target / ".claude" / "commands" / "wiki.md").exists())


if __name__ == "__main__":
    unittest.main()
