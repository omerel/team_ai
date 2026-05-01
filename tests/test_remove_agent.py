import unittest
import sys
import tempfile
import shutil
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setup import scaffold_project, add_agent, remove_agent


class TestRemoveAgent(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = self.tmp / "p"
        with redirect_stdout(StringIO()):
            scaffold_project(self.target, minimal=True, force=False)
            add_agent(self.target, "backend-specialist=rocky")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_removes_specialist(self):
        with redirect_stdout(StringIO()):
            rc = remove_agent(self.target, "rocky")
        self.assertEqual(rc, 0)
        self.assertFalse((self.target / ".claude" / "agents" / "backend-specialist.md").exists())
        self.assertNotIn("@rocky", (self.target / ".claude" / "team.md").read_text())

    def test_refuses_to_remove_core(self):
        with self.assertRaises(SystemExit):
            with redirect_stdout(StringIO()):
                remove_agent(self.target, "planner")
        self.assertTrue((self.target / ".claude" / "agents" / "planner.md").exists())

    def test_rejects_unknown_nickname(self):
        with self.assertRaises(SystemExit):
            with redirect_stdout(StringIO()):
                remove_agent(self.target, "nobody")


if __name__ == "__main__":
    unittest.main()
