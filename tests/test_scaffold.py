import unittest
import tempfile
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setup import scaffold_project, MINIMAL_AGENTS


class TestScaffoldMinimal(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = self.tmp / "myproject"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_minimal_creates_full_tree(self):
        rc = scaffold_project(self.target, minimal=True, force=False)
        self.assertEqual(rc, 0)

        # Top-level dirs
        for d in (".claude", "src", "resource", "sprints"):
            self.assertTrue((self.target / d).is_dir(), f"missing {d}")

        # Standard files
        self.assertTrue((self.target / "CLAUDE.md").is_file())
        self.assertTrue((self.target / "resource" / "README.md").is_file())
        self.assertTrue((self.target / ".claude" / "team.md").is_file())
        self.assertTrue((self.target / ".claude" / "settings.json").is_file())
        self.assertTrue((self.target / ".claude" / "scripts" / "team_setup.py").is_file())

        # Slash commands
        for cmd in ("sprint-start", "sprint-status", "sprint-close",
                    "sprint-resume", "sprint-board"):
            self.assertTrue(
                (self.target / ".claude" / "commands" / f"{cmd}.md").is_file(),
                f"missing command {cmd}",
            )

        # Sprint-board generator
        self.assertTrue((self.target / ".claude" / "scripts" / "board.py").is_file())
        self.assertTrue(
            (self.target / ".claude" / "scripts" / "sprint-board.template.html").is_file()
        )

        # Agents (only MINIMAL set installed)
        agents_dir = self.target / ".claude" / "agents"
        installed = {p.stem for p in agents_dir.glob("*.md")}
        self.assertEqual(installed, set(MINIMAL_AGENTS))

        # Skills folder exists with content
        skills_dir = self.target / ".claude" / "skills"
        self.assertTrue(skills_dir.is_dir())
        self.assertGreaterEqual(len(list(skills_dir.iterdir())), 12)

    def test_minimal_renders_no_unrendered_vars(self):
        scaffold_project(self.target, minimal=True, force=False)
        # CLAUDE.md should have no leftover $vars
        text = (self.target / "CLAUDE.md").read_text()
        self.assertNotIn("$project_name", text)
        self.assertNotIn("$description", text)
        # An installed agent file should have no leftover $vars
        planner = (self.target / ".claude" / "agents" / "planner.md").read_text()
        self.assertNotIn("$nickname", planner)
        self.assertNotIn("$role", planner)

    def test_refuses_existing_target_without_force(self):
        self.target.mkdir(parents=True)
        (self.target / ".claude").mkdir()
        with self.assertRaises(SystemExit):
            scaffold_project(self.target, minimal=True, force=False)

    def test_force_overwrites_existing(self):
        self.target.mkdir(parents=True)
        (self.target / ".claude").mkdir()
        rc = scaffold_project(self.target, minimal=True, force=True)
        self.assertEqual(rc, 0)

    def test_in_place_templates_bundled_without_skills(self):
        """In-place ops (rename, add-agent) need templates next to the script.

        Skills are NOT bundled here — they already live at .claude/skills/.
        """
        scaffold_project(self.target, minimal=True, force=False)
        bundled = self.target / ".claude" / "scripts" / "template"
        self.assertTrue((bundled / "CLAUDE.md.tmpl").is_file())
        self.assertTrue((bundled / "claude" / "team.md.tmpl").is_file())
        self.assertTrue((bundled / "claude" / "agents" / "planner.md.tmpl").is_file())
        # All 13 agent templates available so --add-agent works for any role
        agent_tmpls = list((bundled / "claude" / "agents").glob("*.md.tmpl"))
        self.assertEqual(len(agent_tmpls), 13)
        # Skills are NOT duplicated under scripts/template/
        self.assertFalse((bundled / "claude" / "skills").exists())


if __name__ == "__main__":
    unittest.main()
