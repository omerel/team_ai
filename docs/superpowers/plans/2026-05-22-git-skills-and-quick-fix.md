# Git Skills, Commit Attribution, Sprint Branching & Quick-Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the team_ai scaffolder first-class git support — a `using-git` skill, `@<nickname>:` commit attribution wired into agents, automatic `sprint/<slug>` branches, and a lightweight `/quick-fix` command — all shipped through the template that `setup.py` generates.

**Architecture:** All behavior lives in the `template/` tree that `setup.py` copies/renders into new projects. Skills and commands are copied verbatim (adding a folder/file ships it); agents are rendered from `*.md.tmpl` with `$nickname`/`$project_name` substitution; `CLAUDE.md.tmpl` and `settings.json` are template files. Tests assert on the *output* of `scaffold_project(...)` and on the template files directly, following the existing `tests/test_scaffold.py` pattern (stdlib `unittest` + `tempfile`).

**Tech Stack:** Python 3.8+ standard library only; `unittest` for tests; Markdown + JSON template files.

---

## Spec reference

Design spec: `docs/superpowers/specs/2026-05-22-git-skills-and-quick-fix-design.md`

## File structure

New files:
- `template/claude/skills/using-git/SKILL.md` — the git conventions skill (auto-copied by `_copy_dir`).
- `template/claude/commands/quick-fix.md` — the `/quick-fix` slash command (auto-copied).
- `tests/test_git_workflow.py` — all new tests.

Modified files:
- `template/claude/settings.json` — add git Bash permissions.
- `template/claude/agents/*.md.tmpl` — 10 writing agents reference `using-git` + attribution.
- `template/claude/commands/sprint-start.md` — create/switch to `sprint/<slug>`.
- `template/claude/commands/sprint-close.md` — report-only branch reporting on PASS.
- `template/CLAUDE.md.tmpl` — `/quick-fix` in command list, "Git & Version Control" section, `fixes/` convention.
- `README.md` — document git attribution, branching, `/quick-fix`, and `using-git`.

The 10 "writing agents" that commit (per spec): `planner`, `reviewer`, `architect`, `implementer`, `backend-specialist`, `frontend-specialist`, `qa-engineer`, `devops`, `documenter`, `data-ml-engineer`. (`researcher` and `security-reviewer` are excluded — they don't author commits.)

---

## Task 1: `using-git` skill

**Files:**
- Create: `template/claude/skills/using-git/SKILL.md`
- Test: `tests/test_git_workflow.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_git_workflow.py`:

```python
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
        scaffold_project(target, minimal=True, force=False)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_git_workflow -v`
Expected: FAIL — `AssertionError: False is not true` (skill file does not exist yet).

- [ ] **Step 3: Create the skill**

Create `template/claude/skills/using-git/SKILL.md`:

```markdown
---
name: using-git
description: Use when committing your work, attributing a commit to yourself, or working on a sprint or quick-fix branch — defines the team's commit-attribution and clean-commit rules.
---

# Using Git

You are a teammate committing to the guide's shared git history. Because every
commit lands on the guide's git identity, your commits MUST be attributed to you.

## Attribution (required)

Every commit subject MUST start with your nickname followed by `: `.

```
@<your-nickname>: <imperative summary>
```

Example: `@rocky: fix pagination off-by-one`. You know your nickname from your
own agent prompt. Never commit without this prefix.

## Clean commits

- One focused change per commit. Do not stage unrelated files.
- Imperative subject line ("add", "fix", "rename"), not past tense.
- Run `git status` and `git diff --staged` before committing to confirm exactly
  what you are about to record.

## Branch awareness

- Check the current branch (`git status`) before committing. Sprint work belongs
  on the active `sprint/<slug>` branch — do NOT switch branches unless your task
  explicitly tells you to.
- A `/quick-fix` commits on whatever branch is currently checked out.

## Safety

- Never force-push and never rewrite published history unless the guide
  explicitly asks for it.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_git_workflow -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add template/claude/skills/using-git/SKILL.md tests/test_git_workflow.py
git commit -m "feat: add using-git skill with commit-attribution convention"
```

---

## Task 2: Git permissions in `settings.json`

**Files:**
- Modify: `template/claude/settings.json`
- Test: `tests/test_git_workflow.py`

- [ ] **Step 1: Write the failing test**

Append this class to `tests/test_git_workflow.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_git_workflow.TestGitPermissions -v`
Expected: FAIL — `AssertionError: ... missing permission Bash(git add:*)`.

- [ ] **Step 3: Update settings.json**

Replace the entire contents of `template/claude/settings.json` with:

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Write",
      "Edit",
      "Bash(ls:*)",
      "Bash(find:*)",
      "Bash(cat:*)",
      "Bash(grep:*)",
      "Bash(rg:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Bash(git checkout:*)",
      "Bash(git branch:*)",
      "Bash(git switch:*)"
    ]
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_git_workflow.TestGitPermissions -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add template/claude/settings.json tests/test_git_workflow.py
git commit -m "feat: allow git commands in scaffolded settings.json"
```

---

## Task 3: `/quick-fix` command

**Files:**
- Create: `template/claude/commands/quick-fix.md`
- Test: `tests/test_git_workflow.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_git_workflow.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_git_workflow.TestQuickFixCommand -v`
Expected: FAIL — `AssertionError: False is not true` (command file does not exist).

- [ ] **Step 3: Create the command**

Create `template/claude/commands/quick-fix.md`:

```markdown
---
description: Make a small, documented fix without a full sprint
argument-hint: "\"<description>\" [@nickname]"
---

Make a quick fix: $ARGUMENTS

A quick-fix is lighter than a sprint: no planner, no reviewer, no branch, no
approval gates. One agent makes the change, records it, and commits.

Steps:
1. Parse `$ARGUMENTS` into a `<description>` (quoted) and an optional `@nickname`.
2. Read `.claude/team.md` for the valid nicknames. Resolve the assignee:
   - If an `@nickname` was given, validate it against `team.md`.
   - Else default to the `implementer` nickname **if installed**.
   - Else (no `@nickname` and no `implementer`): refuse and ask the guide to name
     an assignee, listing the valid nicknames from `team.md`. Stop.
3. Generate a slug from the description: lowercase, `[a-z0-9-]` only, max 40 chars
   (same rules as `/sprint-start`). If `fixes/<YYYY-MM-DD>_<slug>.md` already
   exists, append `-2`, `-3`, etc.
4. Dispatch the resolved agent (one subagent) with this prompt:
   - "Quick fix: <description>. Read CLAUDE.md, .claude/team.md, and any relevant
     resource/ and src/ files. Make the change. Invoke the `using-git` skill and
     commit on the **current branch** with subject `@<nickname>: <description>`.
     Then write `fixes/<YYYY-MM-DD>_<slug>.md` using the Quick Fix format in
     CLAUDE.md (by @<nickname>, change, result, commit SHA). Create `fixes/` if it
     does not exist. Return a one-paragraph summary with the commit SHA."
5. After the agent returns, report the fix summary and commit SHA to the guide.

Note: with an active sprint, the fix commits onto the current (sprint) branch by
design — quick-fix stays on whatever branch is checked out.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_git_workflow.TestQuickFixCommand -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add template/claude/commands/quick-fix.md tests/test_git_workflow.py
git commit -m "feat: add /quick-fix command for lightweight documented changes"
```

---

## Task 4: Wire `using-git` + attribution into the 10 writing agents

**Files:**
- Modify: `template/claude/agents/planner.md.tmpl`, `reviewer.md.tmpl`,
  `architect.md.tmpl`, `implementer.md.tmpl`, `backend-specialist.md.tmpl`,
  `frontend-specialist.md.tmpl`, `qa-engineer.md.tmpl`, `devops.md.tmpl`,
  `documenter.md.tmpl`, `data-ml-engineer.md.tmpl`
- Test: `tests/test_git_workflow.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_git_workflow.py`:

```python
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

    def test_rendered_agent_carries_concrete_nickname(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            target = _scaffold(tmp)
            planner = (target / ".claude" / "agents" / "planner.md").read_text()
            self.assertIn("@planner:", planner)
            self.assertNotIn("@$nickname", planner)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_git_workflow.TestAgentGitWiring -v`
Expected: FAIL — `AssertionError: ... planner missing using-git`.

- [ ] **Step 3: Edit each of the 10 agent templates**

For **every** file listed above, make these two edits:

(a) Add a `using-git` bullet to the "## Your Skills" list. Insert this line as the
last bullet of that section:

```markdown
- **using-git** — invoke whenever you commit. Prefix every commit subject with `@$nickname:`.
```

(b) Add an attribution reminder to the I/O contract. Immediately after the step
that mentions committing/work-log, add this standalone line (keep it un-numbered
so step numbers don't shift):

```markdown
> **Commit attribution:** every commit you make MUST start its subject with `@$nickname:` (see the `using-git` skill).
```

Concrete example for `implementer.md.tmpl` — the "Your Skills" section becomes:

```markdown
## Your Skills (always invoke these for relevant work)

- **superpowers:test-driven-development** — invoke for every code task. Write the failing test first, run it, implement, run again.
- **superpowers:systematic-debugging** — invoke when something doesn't work. Form a hypothesis, isolate, verify, fix.
- **superpowers:receiving-code-review** — invoke when the Reviewer (or another teammate) returns feedback on your work.
- **using-git** — invoke whenever you commit. Prefix every commit subject with `@$nickname:`.
```

and right after I/O contract step 6 ("Return a one-paragraph summary...") add:

```markdown
> **Commit attribution:** every commit you make MUST start its subject with `@$nickname:` (see the `using-git` skill).
```

Apply the equivalent two edits to the other 9 templates. The `using-git` bullet
text and the attribution line are identical in every file; only the surrounding
context differs.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_git_workflow.TestAgentGitWiring -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add template/claude/agents/*.md.tmpl tests/test_git_workflow.py
git commit -m "feat: wire using-git skill and @nickname attribution into writing agents"
```

---

## Task 5: Sprint branching in `/sprint-start`

**Files:**
- Modify: `template/claude/commands/sprint-start.md`
- Test: `tests/test_git_workflow.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_git_workflow.py`:

```python
class TestSprintStartBranch(unittest.TestCase):
    def test_sprint_start_creates_branch(self):
        cmd = (
            REPO_ROOT / "template" / "claude" / "commands" / "sprint-start.md"
        ).read_text()
        self.assertIn("git checkout -b sprint/", cmd)
        self.assertIn(".git", cmd)  # non-git-repo guard documented
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_git_workflow.TestSprintStartBranch -v`
Expected: FAIL — `AssertionError: 'git checkout -b sprint/' not found`.

- [ ] **Step 3: Edit sprint-start.md**

In `template/claude/commands/sprint-start.md`, insert a new step between the
current step 4 (write `.active`) and step 5 (read `team.md`). Renumber the
following steps. The new step:

```markdown
5. Create the sprint branch:
   - If this is not a git repo (no `.git` directory), print a warning that no
     branch was created and continue — do not fail the sprint.
   - Otherwise create and switch to the branch: `git checkout -b sprint/<slug>`
     (use the same deduped `<slug>` as the sprint folder). Any uncommitted changes
     carry over with you. If `sprint/<slug>` already exists, switch to it with
     `git checkout sprint/<slug>` and note that it was reused.
```

After inserting, the previously-numbered steps 5, 6, 7 become 6, 7, 8.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_git_workflow.TestSprintStartBranch -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add template/claude/commands/sprint-start.md tests/test_git_workflow.py
git commit -m "feat: create sprint/<slug> branch on /sprint-start"
```

---

## Task 6: Report-only branch handling in `/sprint-close`

**Files:**
- Modify: `template/claude/commands/sprint-close.md`
- Test: `tests/test_git_workflow.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_git_workflow.py`:

```python
class TestSprintCloseBranch(unittest.TestCase):
    def test_sprint_close_reports_branch_without_merging(self):
        cmd = (
            REPO_ROOT / "template" / "claude" / "commands" / "sprint-close.md"
        ).read_text()
        self.assertIn("sprint branch", cmd.lower())
        self.assertIn("do not merge", cmd.lower())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_git_workflow.TestSprintCloseBranch -v`
Expected: FAIL — `AssertionError: 'sprint branch' not found`.

- [ ] **Step 3: Edit sprint-close.md**

In `template/claude/commands/sprint-close.md`, in the PASS branch of step 4,
expand it to report the branch. Replace this line:

```markdown
   - If PASS: delete `sprints/.active` and tell the guide the sprint is closed.
```

with:

```markdown
   - If PASS: delete `sprints/.active` and tell the guide the sprint is closed.
     Then report the current sprint branch name (`sprint/<slug>`) and suggest next
     steps — merge, open a PR, or keep the branch. **Do not merge automatically.**
     The guide may invoke the `finishing-a-development-branch` skill to decide.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_git_workflow.TestSprintCloseBranch -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add template/claude/commands/sprint-close.md tests/test_git_workflow.py
git commit -m "feat: report sprint branch (no auto-merge) on /sprint-close"
```

---

## Task 7: Document git workflow in `CLAUDE.md.tmpl`

**Files:**
- Modify: `template/CLAUDE.md.tmpl`
- Test: `tests/test_git_workflow.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_git_workflow.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_git_workflow.TestClaudeMdGitDocs -v`
Expected: FAIL — `AssertionError: '/quick-fix' not found in ...`.

- [ ] **Step 3: Edit CLAUDE.md.tmpl**

Make three edits to `template/CLAUDE.md.tmpl`.

(a) In the "### Slash commands" list (§1), add this bullet after the
`/sprint-resume` line:

```markdown
- `/quick-fix "<description>" [@nickname]` — Make a small, documented change without a full sprint. One agent edits, commits on the current branch, and writes a record under `fixes/`.
```

(b) Add a new top-level section immediately after §6 (Team Roster), at the end of
the file:

```markdown
---

## 7. Git & Version Control

### Commit attribution
Every commit an agent makes MUST start its subject with the agent's nickname:
`@<nickname>: <imperative summary>` (e.g. `@rocky: fix pagination off-by-one`).
Because all commits land on the guide's git identity, this prefix is how the
guide tells which teammate authored each commit. Agents follow the `using-git`
skill for this.

### Sprint branches
`/sprint-start` creates and switches to a `sprint/<slug>` branch (same slug as the
sprint folder). All sprint work is committed there. In a non-git directory, branch
creation is skipped with a warning. `/sprint-close` reports the branch name and
suggests next steps (merge / PR / keep) but does **not** merge automatically.

### Quick fixes
`/quick-fix "<description>" [@nickname]` records a small change in
`fixes/<YYYY-MM-DD>_<slug>.md` with this format:

```
# Quick Fix: <description>
**By:** @<nickname>
**Date:** <ISO date>
**Commit:** <sha>

## Change
<what changed and why>

## Result
<tests run / observed outcome>
```
```

(c) In §5 "Sprint File Conventions", add a short subsection after "### Work-logs":

```markdown
### Quick-fix records
Quick fixes are recorded one file per fix at `fixes/<YYYY-MM-DD>_<slug>.md` (slug
rules as above). They are independent of sprints and need no plan or work-log.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_git_workflow.TestClaudeMdGitDocs -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite to confirm nothing regressed**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (existing `test_scaffold.py` skill-count assertion `>= 12` still
holds — `using-git` makes it 13).

- [ ] **Step 6: Commit**

```bash
git add template/CLAUDE.md.tmpl tests/test_git_workflow.py
git commit -m "docs: document git attribution, sprint branches, and quick-fix in CLAUDE template"
```

---

## Task 8: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Edit README.md**

Make these edits to `README.md`:

(a) In the "## Sprint workflow (in a generated project)" section, change step 2
from:

```markdown
2. Run `/sprint-start "your goal"`.
```

to:

```markdown
2. Run `/sprint-start "your goal"` — this also creates a `sprint/<slug>` git branch for the sprint.
```

(b) Add a new section after "## Sprint board (offline kanban)":

```markdown
## Git workflow

Agents commit their own work. Every agent commit is attributed with an
`@<nickname>:` subject prefix (e.g. `@rocky: fix pagination off-by-one`) so you
can see which teammate authored each commit on your git account. `/sprint-start`
opens a `sprint/<slug>` branch; `/sprint-close` reports that branch and suggests
next steps without merging automatically.

### Quick fix

For small changes that don't need a full sprint:

    /quick-fix "correct off-by-one in pagination" @rocky

One agent makes the change, commits it on the current branch, and writes a record
to `fixes/<date>_<slug>.md`. No planner, reviewer, branch, or approval gates.
```

(c) In the "## Bundled skills" section, after the sentence listing the 12
superpowers skills, add:

```markdown

The template also bundles one custom project skill, `using-git`, which defines the
commit-attribution convention agents follow.
```

- [ ] **Step 2: Verify the edits**

Run: `grep -n "quick-fix\|using-git\|sprint/<slug>\|@<nickname>" README.md`
Expected: matches in the sprint workflow, git workflow, and bundled-skills
sections.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document git workflow, quick-fix, and using-git skill in README"
```

---

## Final verification

- [ ] **Run the full test suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: all tests PASS, including the new `tests/test_git_workflow.py`.

- [ ] **Smoke-check a scaffold**

```bash
rm -rf /tmp/team-ai-git-check
python3 setup.py /tmp/team-ai-git-check --minimal
ls /tmp/team-ai-git-check/.claude/skills/using-git/SKILL.md
ls /tmp/team-ai-git-check/.claude/commands/quick-fix.md
grep -c "git" /tmp/team-ai-git-check/.claude/settings.json
grep -n "@implementer:" /tmp/team-ai-git-check/.claude/agents/implementer.md
```
Expected: skill and command files exist; settings.json has git permissions; the
rendered implementer carries `@implementer:`.

---

## Self-review notes

- **Spec coverage:** §1 skill → Task 1; §2 attribution → Tasks 1+4; §3 settings →
  Task 2; §4 sprint branching → Tasks 5+6; §5 quick-fix → Task 3; §6 docs/tests →
  Tasks 7+8 and the per-task tests. The minimal-scaffold "no implementer" edge
  case is handled in Task 3, step 3.
- **Placeholder scan:** all code/content blocks are concrete; `<slug>`,
  `<nickname>`, `<description>` are intended runtime placeholders inside template
  text, not plan gaps.
- **Naming consistency:** branch `sprint/<slug>`, attribution `@<nickname>:` /
  `@$nickname:` (rendered form), record path `fixes/<YYYY-MM-DD>_<slug>.md`, and
  skill name `using-git` are used identically across all tasks and tests.
```
