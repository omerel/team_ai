# Git Workflow, Commit Attribution, Sprint Branching & Quick-Fix — Design

**Date:** 2026-05-22
**Status:** Approved (design)
**Project:** team_ai (multi-agent scaffolder)

## Summary

Add first-class git support to the team_ai framework so that:

1. Agents that write code or content can commit their work through a shared,
   authoritative `using-git` skill.
2. Every agent commit is attributed with an `@<nickname>:` subject prefix, so
   the user can tell which agent authored each commit on their own git account.
3. Starting a sprint automatically creates and switches to a `sprint/<slug>`
   branch.
4. A new lightweight `/quick-fix` command makes small, documented changes
   without the full sprint ceremony.

All changes live in the template that `setup.py` scaffolds into new projects.

## Motivation

The framework already has agents that "commit work" in their I/O contracts, but
there is no git skill, no commit-authorship convention, and no branch isolation.
Because all commits land on the user's git identity, there is currently no way to
attribute a commit to the agent that produced it. Sprints also run directly on
whatever branch is checked out, mixing sprint work into the base branch. Finally,
small one-off fixes are too small to justify a full sprint but should still be
recorded.

## Decisions (resolved during brainstorming)

| Question | Decision |
| --- | --- |
| Git capability packaging | New custom vendored skill `using-git` |
| Attribution location | Commit **subject prefix**: `@<nickname>: <message>` |
| Sprint branch name | `sprint/<slug>` (same deduped slug as sprint folder) |
| Sprint close branch behavior | **Report only** (no auto-merge) |
| Quick-fix documentation | **Per-fix file**: `fixes/<date>_<slug>.md` |
| Quick-fix workflow | **One specialist, no branch** (no planner/reviewer/gates) |

## Components

### 1. New skill: `using-git`

- **Location:** `template/claude/skills/using-git/SKILL.md`.
- **Distribution:** the existing `_copy_dir(TEMPLATE_DIR/claude/skills, ...)` in
  `setup.py` copies all skill folders verbatim, so no scaffolder change is
  required to ship a new skill folder.
- **Frontmatter:** `name: using-git`, with a `description` that triggers on
  committing work, attributing commits, or working on a sprint/fix branch.
- **Content (rules taught):**
  - **Attribution:** every commit subject MUST start with `@<your-nickname>: `
    — e.g. `@rocky: fix pagination off-by-one`. The agent knows its nickname
    from its own prompt.
  - **Clean commits:** one focused change per commit, imperative subject, do not
    stage unrelated files.
  - **Branch awareness:** run `git status` / check the current branch before
    committing; never switch branches unless the task explicitly says so, so
    sprint work lands on the sprint branch.
  - **Safety:** no force-push and no history rewriting unless the guide
    explicitly asks.

Naming follows the existing `using-*` convention and is distinct from the
bundled `using-git-worktrees` skill (which this project does not vendor).

### 2. Commit attribution (`@<nickname>:` subject prefix)

Wired in three places so it is enforced, not merely documented:

- The `using-git` skill is the authoritative rule.
- **Every agent template that writes files** gets:
  - `using-git` added to its "Your Skills" list.
  - A line in its I/O contract: "When you commit, invoke `using-git` and prefix
    the commit subject with `@$nickname:`".
  - Applies to: `implementer`, `backend-specialist`, `frontend-specialist`,
    `qa-engineer`, `devops`, `data-ml-engineer`, `documenter`, `architect`,
    `planner`, `reviewer`. (Planner commits `plan.md`; Reviewer commits the
    closeout — full attribution trail.)
- **CLAUDE.md** states the convention once for the whole team (see Component 6).

The Orchestrator (main Claude session) is not a dispatchable agent and does not
author code commits, so the prefix rule targets dispatched agents only.
Orchestrator-authored commits are out of scope.

### 3. Settings: allow git commands

`template/claude/settings.json` currently allows only read-only Bash. Add to the
`permissions.allow` list so agents can commit and branch without permission
prompts:

- `Bash(git add:*)`
- `Bash(git commit:*)`
- `Bash(git status:*)`
- `Bash(git diff:*)`
- `Bash(git log:*)`
- `Bash(git checkout:*)`
- `Bash(git branch:*)`
- `Bash(git switch:*)`

### 4. Sprint branching

Modify `template/claude/commands/sprint-start.md` so the branch is created right
after the active marker is established. New step ordering:

1. Refuse if a sprint is already active (unchanged).
2. Compute slug + dedup against existing sprint folders (unchanged).
3. **Branch handling (new):**
   - If not a git repo (`.git` missing): skip branch creation, print a warning,
     and continue — do not fail the sprint.
   - Otherwise create and switch to `sprint/<slug>` from the current HEAD
     (`git checkout -b sprint/<slug>`). Any uncommitted changes carry over with
     you (standard git behavior); the command notes this.
   - If `sprint/<slug>` already exists: switch to it and note it (it reuses the
     folder's deduped slug, so this is rare).
4. Create the sprint folder + empty `work-logs/`, write `sprints/.active`
   (unchanged).
5. Read `.claude/team.md` and dispatch the Planner (unchanged).

`/sprint-close` (`template/claude/commands/sprint-close.md`) is **report-only**
for the branch: on PASS, print the sprint branch name and suggest next steps
(merge / open PR / keep). Do not merge automatically. The
`finishing-a-development-branch` skill remains available to the guide.

### 5. `/quick-fix` command

New command file `template/claude/commands/quick-fix.md` (commands are copied
as-is by `setup.py`, so adding the file ships it). Lighter than a sprint: no
planner, no reviewer, no branch, no approval gates.

Invocation: `/quick-fix "<description>" [@nickname]`

Steps:

1. Resolve the assignee: the given `@nickname` (validated against
   `.claude/team.md`), or default to the `implementer` nickname **if it is
   installed**. A minimal scaffold has only the core `planner` and `reviewer`,
   so if no `implementer` is present and no `@nickname` was given, refuse and
   ask the guide to name an assignee, listing the valid nicknames from
   `team.md`.
2. Generate a slug from the description using the same slugify rules as sprints
   (lowercase, `[a-z0-9-]`, max 40 chars). If a `fixes/<date>_<slug>.md` already
   exists for today, append `-2`, `-3`, etc.
3. Dispatch that one agent with a prompt to:
   - Make the change.
   - Write `fixes/<YYYY-MM-DD>_<slug>.md` (format below), creating `fixes/` on
     demand.
   - Commit on the **current branch** with subject `@<nickname>: <description>`.
4. Report the result + commit SHA to the guide.

Per-fix file format:

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

Note: when a sprint is active, a quick-fix commits onto the current (sprint)
branch by design — quick-fix is for small in-context changes and stays on
whatever branch is checked out.

### 6. Docs, scaffolder & tests

- **`template/CLAUDE.md.tmpl`:**
  - Add `/quick-fix <description> [@nickname]` to the slash-commands list.
  - Add a "Git & Version Control" section covering: the `@<nickname>:` commit
    convention, the auto-created `sprint/<slug>` branch, and report-only close.
  - Add `fixes/<YYYY-MM-DD>_<slug>.md` to the file conventions section.
- **`README.md`:** mention git attribution, sprint branching, and `/quick-fix`.
  Document `using-git` as a custom project skill bundled alongside the 12
  vendored superpowers skills (it is not itself a superpowers skill, so keep the
  "12 superpowers skills" wording accurate and list `using-git` separately).
- **`setup.py`:** no structural change expected — skills are auto-copied,
  commands are auto-copied, agents are re-rendered from the edited templates.
  Verify nothing hardcodes the skill list or count in a way that needs updating.
- **`tests/`:** add assertions that a scaffolded project contains:
  - `.claude/skills/using-git/SKILL.md`
  - `.claude/commands/quick-fix.md`
  - the git entries in `.claude/settings.json`
  - rendered agent files that reference `using-git` and the `@<nickname>` prefix
    convention.

## Out of scope (YAGNI)

- Auto-merge or PR automation at sprint close.
- A dedicated branch for quick-fixes.
- A separate reviewer pass for quick-fixes.
- Orchestrator-authored commit attribution.

## Acceptance criteria

- A freshly scaffolded project contains the `using-git` skill, the `quick-fix`
  command, and git permissions in `settings.json`.
- Running `/sprint-start "<goal>"` in a git repo creates and switches to
  `sprint/<slug>`; in a non-git directory it warns and continues.
- Agents reference `using-git` and prefix commit subjects with `@<nickname>:`.
- `/quick-fix "<desc>" [@nickname]` produces a `fixes/<date>_<slug>.md` record
  and a single attributed commit on the current branch.
- `/sprint-close` reports the branch name without auto-merging.
- The test suite covers the presence of the new skill, command, settings, and
  agent references.
