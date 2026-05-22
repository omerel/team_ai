import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from setup import scaffold_project


def _scaffold(tmp):
    target = tmp / "p"
    with redirect_stdout(StringIO()):
        rc = scaffold_project(target, minimal=True, force=False)
    assert rc == 0, f"scaffold failed with rc={rc}"
    return target


class TestUsingGitSkill(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = _scaffold(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_skill_present_with_attribution_rule(self):
        skill = self.target / ".claude" / "skills" / "using-git" / "SKILL.md"
        self.assertTrue(skill.is_file())
        text = skill.read_text()
        self.assertIn("name: using-git", text)
        self.assertIn("@<your-nickname>", text)


if __name__ == "__main__":
    unittest.main()
