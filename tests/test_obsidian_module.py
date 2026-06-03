import unittest
import tempfile
import shutil
import sys
import json
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


class TestObsidianEnabled(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = self.tmp / "proj"
        scaffold_project(self.target, minimal=True, force=False, obsidian=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_skills_commands_agents_present(self):
        c = self.target / ".claude"
        for skill in ("wiki", "wiki-ingest", "wiki-query", "wiki-lint", "save",
                      "canvas", "defuddle", "think", "obsidian-markdown",
                      "obsidian-bases"):
            self.assertTrue((c / "skills" / skill / "SKILL.md").is_file(),
                            f"missing skill {skill}")
        for cmd in ("wiki", "save", "canvas"):
            self.assertTrue((c / "commands" / f"{cmd}.md").is_file(),
                            f"missing command {cmd}")
        for agent in ("verifier", "wiki-ingest", "wiki-lint"):
            self.assertTrue((c / "agents" / f"{agent}.md").is_file(),
                            f"missing agent {agent}")

    def test_scripts_and_templates_present(self):
        c = self.target / ".claude"
        for s in ("detect-transport.sh", "wiki-lock.sh", "setup-vault.sh"):
            self.assertTrue((c / "scripts" / s).is_file(), f"missing script {s}")
        for t in ("source", "entity", "concept", "question", "comparison"):
            self.assertTrue((c / "templates" / f"{t}.md").is_file(),
                            f"missing template {t}")

    def test_wiki_seed_at_project_root(self):
        w = self.target / "wiki"
        for f in ("index.md", "hot.md", "log.md", "overview.md"):
            self.assertTrue((w / f).is_file(), f"missing wiki/{f}")
        for d in ("concepts", "entities", "sources", "questions", "comparisons"):
            self.assertTrue((w / d).is_dir(), f"missing wiki/{d}/")

    def test_claude_md_has_vault_section(self):
        text = (self.target / "CLAUDE.md").read_text()
        self.assertIn("Knowledge Vault", text)
        self.assertIn("/wiki", text)
        self.assertNotIn("$obsidian_", text)

    def test_settings_has_extra_permissions_and_hooks_no_autocommit(self):
        settings = json.loads((self.target / ".claude" / "settings.json").read_text())
        allow = settings["permissions"]["allow"]
        self.assertIn("Bash(.claude/scripts/wiki-lock.sh:*)", allow)
        self.assertIn("Read", allow)  # original permissions preserved
        hooks = settings["hooks"]
        self.assertEqual(set(hooks), {"SessionStart", "PostCompact", "Stop"})
        self.assertNotIn("PostToolUse", hooks)
        self.assertNotIn("auto-commit", json.dumps(hooks))

    def test_gitignore_has_vault_meta(self):
        gi = (self.target / ".gitignore").read_text()
        self.assertIn(".vault-meta/", gi)


from setup import add_obsidian


class TestObsidianInPlace(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.target = self.tmp / "proj"
        scaffold_project(self.target, minimal=True, force=False)  # plain

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_add_obsidian_matches_with_obsidian(self):
        rc = add_obsidian(self.target)
        self.assertEqual(rc, 0)
        c = self.target / ".claude"
        self.assertTrue((c / "skills" / "wiki" / "SKILL.md").is_file())
        self.assertTrue((c / "commands" / "wiki.md").is_file())
        self.assertTrue((c / "agents" / "verifier.md").is_file())
        self.assertTrue((self.target / "wiki" / "hot.md").is_file())
        settings = json.loads((c / "settings.json").read_text())
        self.assertEqual(set(settings["hooks"]),
                         {"SessionStart", "PostCompact", "Stop"})
        self.assertIn("Knowledge Vault", (self.target / "CLAUDE.md").read_text())
        self.assertIn("obsidian:module:start",
                      (self.target / "CLAUDE.md").read_text())

    def test_add_obsidian_is_idempotent(self):
        add_obsidian(self.target)
        claude_once = (self.target / "CLAUDE.md").read_text()
        settings_once = (self.target / ".claude" / "settings.json").read_text()
        add_obsidian(self.target)  # run again
        claude_twice = (self.target / "CLAUDE.md").read_text()
        settings_twice = (self.target / ".claude" / "settings.json").read_text()
        self.assertEqual(claude_once.count("obsidian:module:start"),
                         claude_twice.count("obsidian:module:start"))
        self.assertEqual(claude_once, claude_twice)
        self.assertEqual(settings_once, settings_twice)


if __name__ == "__main__":
    unittest.main()
