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


class TestGitPermissions(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = _scaffold(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_settings_allow_git_commands(self):
        settings = json.loads(
            (self.target / ".claude" / "settings.json").read_text()
        )
        allow = settings["permissions"]["allow"]
        for entry in (
            "Bash(git add:*)",
            "Bash(git commit:*)",
            "Bash(git status:*)",
            "Bash(git diff:*)",
            "Bash(git log:*)",
            "Bash(git checkout:*)",
            "Bash(git branch:*)",
            "Bash(git switch:*)",
        ):
            self.assertIn(entry, allow, f"missing permission {entry}")


class TestQuickFixCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = _scaffold(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_quick_fix_command_present(self):
        cmd = self.target / ".claude" / "commands" / "quick-fix.md"
        self.assertTrue(cmd.is_file())
        text = cmd.read_text()
        # documents the fixes/ record, attribution, and current-branch commit
        self.assertIn("fixes/", text)
        self.assertIn("@<nickname>:", text)
        self.assertIn("current branch", text)


GIT_AGENTS = (
    "planner", "reviewer", "architect", "implementer",
    "backend-specialist", "frontend-specialist", "qa-engineer",
    "devops", "documenter", "data-ml-engineer",
)


class TestAgentGitWiring(unittest.TestCase):
    def test_templates_reference_skill_and_attribution(self):
        tmpl_dir = REPO_ROOT / "template" / "claude" / "agents"
        for role in GIT_AGENTS:
            text = (tmpl_dir / f"{role}.md.tmpl").read_text()
            self.assertIn("using-git", text, f"{role} missing using-git")
            self.assertIn("@$nickname:", text, f"{role} missing @$nickname: prefix")

    def test_rendered_agents_carry_concrete_nickname(self):
        # Writing agents present in a minimal scaffold (MINIMAL_AGENTS ∩ GIT_AGENTS).
        minimal_git_agents = (
            "planner", "reviewer", "architect",
            "implementer", "qa-engineer", "documenter",
        )
        tmp = Path(tempfile.mkdtemp())
        try:
            target = _scaffold(tmp)
            agents_dir = target / ".claude" / "agents"
            for role in minimal_git_agents:
                text = (agents_dir / f"{role}.md").read_text()
                self.assertIn("using-git", text, f"{role} rendered without using-git")
                self.assertIn(
                    "Commit attribution", text,
                    f"{role} rendered without attribution line",
                )
                self.assertNotIn(
                    "@$nickname", text,
                    f"{role} has an unsubstituted @$nickname",
                )
            # planner's concrete nickname is 'planner'
            self.assertIn("@planner:", (agents_dir / "planner.md").read_text())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestSprintStartBranch(unittest.TestCase):
    def test_sprint_start_creates_branch(self):
        cmd = (
            REPO_ROOT / "template" / "claude" / "commands" / "sprint-start.md"
        ).read_text()
        self.assertIn("git checkout -b sprint/", cmd)
        self.assertIn(".git", cmd)  # non-git-repo guard documented


class TestSprintCloseBranch(unittest.TestCase):
    def test_sprint_close_reports_branch_without_merging(self):
        cmd = (
            REPO_ROOT / "template" / "claude" / "commands" / "sprint-close.md"
        ).read_text()
        self.assertIn("sprint branch", cmd.lower())
        self.assertIn("do not merge", cmd.lower())


class TestClaudeMdGitDocs(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = _scaffold(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_claude_md_documents_git_workflow(self):
        text = (self.target / "CLAUDE.md").read_text()
        self.assertIn("/quick-fix", text)
        self.assertIn("Git & Version Control", text)
        self.assertIn("sprint/<slug>", text)
        self.assertIn("fixes/", text)
        self.assertIn("@<nickname>:", text)


if __name__ == "__main__":
    unittest.main()
