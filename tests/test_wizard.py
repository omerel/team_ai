import unittest
import builtins
import sys
import tempfile
import shutil
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setup import run_wizard, scaffold_project


class TestWizard(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = self.tmp / "myproject"
        self._saved_input = builtins.input

    def tearDown(self):
        builtins.input = self._saved_input
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _scripted_input(self, answers):
        it = iter(answers)
        builtins.input = lambda prompt="": next(it)

    def test_collects_minimal_answers_uses_defaults(self):
        answers = [""]
        answers += [""]
        answers.append("n")  # obsidian module: no
        for _ in range(10):
            answers.append("n")
        answers += ["", ""]
        answers.append("y")
        self._scripted_input(answers)
        with redirect_stdout(StringIO()):
            project_name, description, roster, obsidian = run_wizard(self.target)
        self.assertFalse(obsidian)
        self.assertEqual(project_name, "myproject")
        self.assertEqual(description, "")
        self.assertEqual(set(roster.keys()), {"planner", "reviewer"})
        self.assertEqual(roster["planner"], "planner")
        self.assertEqual(roster["reviewer"], "reviewer")

    def test_custom_nicknames_collected(self):
        answers = ["MyApp", "a cool app"]
        answers.append("n")  # obsidian module: no
        for _ in range(10):
            answers.append("n")
        answers += ["paula", "robin"]
        answers.append("y")
        self._scripted_input(answers)
        with redirect_stdout(StringIO()):
            project_name, description, roster, _ = run_wizard(self.target)
        self.assertEqual(project_name, "MyApp")
        self.assertEqual(description, "a cool app")
        self.assertEqual(roster, {"planner": "paula", "reviewer": "robin"})

    def test_rejects_invalid_nickname_then_accepts_valid(self):
        answers = ["", ""]
        answers.append("n")  # obsidian module: no
        for _ in range(10):
            answers.append("n")
        answers += ["Paula", "paula"]
        answers += [""]
        answers.append("y")
        self._scripted_input(answers)
        with redirect_stdout(StringIO()):
            _, _, roster, _ = run_wizard(self.target)
        self.assertEqual(roster["planner"], "paula")

    def test_full_roster_when_user_says_yes(self):
        answers = ["", ""]
        answers.append("n")  # obsidian module: no
        for _ in range(10):
            answers.append("y")
        for _ in range(12):
            answers.append("")
        answers.append("y")
        self._scripted_input(answers)
        with redirect_stdout(StringIO()):
            _, _, roster, _ = run_wizard(self.target)
        self.assertEqual(len(roster), 12)


if __name__ == "__main__":
    unittest.main()
