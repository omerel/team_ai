import unittest
import sys
import builtins
import tempfile
import shutil
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setup import scaffold_project, add_agent


class TestAddAgent(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = self.tmp / "p"
        with redirect_stdout(StringIO()):
            scaffold_project(self.target, minimal=True, force=False)
        self._saved_input = builtins.input

    def tearDown(self):
        builtins.input = self._saved_input
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_add_with_explicit_nickname(self):
        with redirect_stdout(StringIO()):
            rc = add_agent(self.target, "backend-specialist=rocky")
        self.assertEqual(rc, 0)
        self.assertTrue((self.target / ".claude" / "agents" / "backend-specialist.md").is_file())
        self.assertIn("@rocky", (self.target / ".claude" / "team.md").read_text())

    def test_add_prompts_for_nickname_when_omitted(self):
        builtins.input = lambda prompt="": "rocky"
        with redirect_stdout(StringIO()):
            rc = add_agent(self.target, "backend-specialist")
        self.assertEqual(rc, 0)
        self.assertIn("@rocky", (self.target / ".claude" / "team.md").read_text())

    def test_rejects_unknown_role(self):
        with self.assertRaises(SystemExit):
            with redirect_stdout(StringIO()):
                add_agent(self.target, "not-a-real-role")

    def test_already_installed_is_idempotent(self):
        with redirect_stdout(StringIO()):
            rc = add_agent(self.target, "planner")
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
