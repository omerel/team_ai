import unittest
import sys
import tempfile
import shutil
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setup import scaffold_project, list_team


class TestListTeam(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = self.tmp / "p"
        with redirect_stdout(StringIO()):
            scaffold_project(self.target, minimal=True, force=False)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_prints_roster(self):
        buf = StringIO()
        with redirect_stdout(buf):
            rc = list_team(self.target)
        self.assertEqual(rc, 0)
        self.assertIn("@planner", buf.getvalue())
        self.assertIn("@reviewer", buf.getvalue())

    def test_refuses_non_project(self):
        empty = self.tmp / "empty"
        empty.mkdir()
        with self.assertRaises(SystemExit):
            list_team(empty)


if __name__ == "__main__":
    unittest.main()
