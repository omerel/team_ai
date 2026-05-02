import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent / "template" / "claude" / "scripts"),
)
import board  # noqa: E402


SAMPLE_PLAN = """# Sprint: Build the offline kanban board

**Started:** 2026-05-02
**Goal:** Render an offline kanban for the active sprint.

## Tasks

- [ ] **T1** [pending] @planner — Draft the plan.
  - Acceptance: plan.md committed.
  - Notes: keep tasks atomic.

- [x] **T2** [done] @architect — Pick the rendering approach.
  - Acceptance: design doc captures choice.

- [ ] **T3** [in_progress] @frontend — Build the HTML shell.

- [ ] **T4** [blocked] @devops — Wire CI lint.
  - Notes: blocked on linter choice.

## Routing Overrides

(empty)
"""


class TestParseHeader(unittest.TestCase):
    def test_parses_goal_and_started(self):
        sprint = board.parse_plan(SAMPLE_PLAN)
        self.assertEqual(sprint["goal"], "Build the offline kanban board")
        self.assertEqual(sprint["started"], "2026-05-02")


class TestParseTasks(unittest.TestCase):
    def test_parses_all_statuses_with_acceptance_and_notes(self):
        sprint = board.parse_plan(SAMPLE_PLAN)
        tasks = sprint["tasks"]
        self.assertEqual(len(tasks), 4)

        t1 = tasks[0]
        self.assertEqual(t1["id"], "T1")
        self.assertEqual(t1["status"], "pending")
        self.assertEqual(t1["assignee"], "planner")
        self.assertEqual(t1["desc"], "Draft the plan.")
        self.assertEqual(t1["acceptance"], "plan.md committed.")
        self.assertEqual(t1["notes"], "keep tasks atomic.")

        statuses = [t["status"] for t in tasks]
        self.assertEqual(statuses, ["pending", "done", "in_progress", "blocked"])

        t3 = tasks[2]
        self.assertIsNone(t3["acceptance"])
        self.assertIsNone(t3["notes"])

        t4 = tasks[3]
        self.assertEqual(t4["notes"], "blocked on linter choice.")
        self.assertIsNone(t4["acceptance"])

    def test_no_tasks_section_returns_empty_list(self):
        text = "# Sprint: x\n\n**Started:** 2026-01-01\n\n(no tasks section)\n"
        sprint = board.parse_plan(text)
        self.assertEqual(sprint["tasks"], [])


class TestParseTeam(unittest.TestCase):
    def test_parses_roster_block(self):
        text = """
# Team — Project

## Roster

- **@planner** — planner: Plans sprints.
- **@rocky** — backend-specialist: APIs and data.
- **@frontend** — frontend-specialist: UI.
"""
        team = board.parse_team(text)
        self.assertEqual(team, {
            "planner": "planner",
            "rocky": "backend-specialist",
            "frontend": "frontend-specialist",
        })


class TestRenderHtml(unittest.TestCase):
    def _sample_sprint(self):
        return {
            "project_name": "Demo",
            "folder": "2026-05-02_demo",
            "goal": "Test render",
            "started": "2026-05-02",
            "team": {"planner": "planner"},
            "tasks": [{
                "id": "T1", "status": "done", "assignee": "planner",
                "desc": "Hello", "acceptance": None, "notes": None,
            }],
        }

    def test_embeds_json_payload(self):
        html = board.render_html(self._sample_sprint())
        self.assertIn("const SPRINT =", html)
        self.assertNotIn("__SPRINT_DATA__", html)
        m = re.search(r"const SPRINT\s*=\s*(\{.*?\});", html, re.DOTALL)
        self.assertIsNotNone(m, "could not find embedded SPRINT json")
        data = json.loads(m.group(1))
        self.assertEqual(data["goal"], "Test render")
        self.assertEqual(data["tasks"][0]["id"], "T1")

    def test_no_external_assets(self):
        html = board.render_html(self._sample_sprint())
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotRegex(html, r'<link\s[^>]*href="https?://')
        self.assertNotRegex(html, r'<script\s[^>]*src="https?://')


class TestLoadSprint(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / ".claude").mkdir()
        (self.tmp / ".claude" / "team.md").write_text(
            "## Roster\n\n- **@planner** — planner: Plans sprints.\n"
        )
        (self.tmp / "sprints").mkdir()
        (self.tmp / "CLAUDE.md").write_text("# Demo — Team Workflow\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_empty_state_when_no_active_sprint(self):
        sprint = board.load_sprint(self.tmp)
        self.assertEqual(sprint["project_name"], "Demo")
        self.assertIsNone(sprint["folder"])
        self.assertEqual(sprint["tasks"], [])
        self.assertEqual(sprint["team"], {"planner": "planner"})

    def test_loads_active_sprint(self):
        folder = "2026-05-02_demo"
        (self.tmp / "sprints" / folder).mkdir()
        (self.tmp / "sprints" / folder / "plan.md").write_text(SAMPLE_PLAN)
        (self.tmp / "sprints" / ".active").write_text(folder)

        sprint = board.load_sprint(self.tmp)
        self.assertEqual(sprint["folder"], folder)
        self.assertEqual(sprint["goal"], "Build the offline kanban board")
        self.assertEqual(len(sprint["tasks"]), 4)

    def test_active_pointing_at_missing_folder_falls_back_to_empty(self):
        (self.tmp / "sprints" / ".active").write_text("nope-2026")
        sprint = board.load_sprint(self.tmp)
        self.assertIsNone(sprint["folder"])
        self.assertEqual(sprint["tasks"], [])


class TestMain(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / ".claude").mkdir()
        (self.tmp / ".claude" / "team.md").write_text(
            "## Roster\n\n- **@planner** — planner: Plans sprints.\n"
        )
        (self.tmp / "sprints").mkdir()
        (self.tmp / "CLAUDE.md").write_text("# Demo — Team Workflow\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_main_writes_html_and_returns_zero(self):
        rc = board.main(["--no-open"], project=self.tmp)
        self.assertEqual(rc, 0)
        out = self.tmp / "sprint-board.html"
        self.assertTrue(out.is_file())
        text = out.read_text(encoding="utf-8")
        self.assertIn("const SPRINT =", text)
        self.assertNotIn("__SPRINT_DATA__", text)

    def test_main_errors_when_not_a_team_ai_project(self):
        bare = Path(tempfile.mkdtemp())
        try:
            rc = board.main(["--no-open"], project=bare)
            self.assertNotEqual(rc, 0)
        finally:
            shutil.rmtree(bare, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
