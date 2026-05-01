import unittest
import sys
import tempfile
import shutil
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setup import scaffold_project, rename_agent


class TestRename(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = self.tmp / "p"
        with redirect_stdout(StringIO()):
            scaffold_project(self.target, minimal=True, force=False)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_renames_planner(self):
        with redirect_stdout(StringIO()):
            rc = rename_agent(self.target, "planner=paula")
        self.assertEqual(rc, 0)

        text = (self.target / ".claude" / "agents" / "planner.md").read_text()
        self.assertIn("name: paula", text)
        self.assertNotIn("name: planner", text)

        team = (self.target / ".claude" / "team.md").read_text()
        self.assertIn("@paula", team)
        self.assertNotIn("@planner", team)

    def test_renames_existing_work_log(self):
        sprint = self.target / "sprints" / "2026-05-01_test"
        (sprint / "work-logs").mkdir(parents=True)
        (sprint / "work-logs" / "planner.md").write_text("hello")
        with redirect_stdout(StringIO()):
            rename_agent(self.target, "planner=paula")
        self.assertTrue((sprint / "work-logs" / "paula.md").is_file())
        self.assertFalse((sprint / "work-logs" / "planner.md").is_file())

    def test_rejects_unknown_old(self):
        with self.assertRaises(SystemExit):
            with redirect_stdout(StringIO()):
                rename_agent(self.target, "nonexistent=x")

    def test_rejects_collision(self):
        with self.assertRaises(SystemExit):
            with redirect_stdout(StringIO()):
                rename_agent(self.target, "planner=reviewer")

    def test_rejects_invalid_new_nickname(self):
        with self.assertRaises(SystemExit):
            with redirect_stdout(StringIO()):
                rename_agent(self.target, "planner=Bad-Name")

    def test_rejects_bad_format(self):
        with self.assertRaises(SystemExit):
            with redirect_stdout(StringIO()):
                rename_agent(self.target, "no-equals-sign")


if __name__ == "__main__":
    unittest.main()
