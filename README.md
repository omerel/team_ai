# Team-AI Multi-Agent Framework

A reusable `.claude/` template plus a stdlib-only Python scaffolder that drops a multi-agent project workspace into any directory. The team — a Planner, a Reviewer, and a configurable roster of specialists — runs sprints under the coordination of an Orchestrator (the main Claude Code session). All state lives in plain files.

## Quick start

```bash
# Interactive scaffolder (default)
python3 setup.py /path/to/new-project

# Non-interactive with sensible defaults
python3 setup.py /path/to/new-project --minimal

# Overwrite an existing .claude/
python3 setup.py /path/to/new-project --force

# Include the opt-in Obsidian knowledge-vault module
python3 setup.py /path/to/new-project --with-obsidian
```

## In-place operations

After a project is generated, run these from inside it (or pass the project path as the first argument):

```bash
python3 .claude/scripts/team_setup.py --list-team
python3 .claude/scripts/team_setup.py --rename rocky=ricky
python3 .claude/scripts/team_setup.py --add-agent backend-specialist
python3 .claude/scripts/team_setup.py --add-agent backend-specialist=rocky
python3 .claude/scripts/team_setup.py --remove-agent rocky
python3 .claude/scripts/team_setup.py --add-obsidian
```

## Sprint workflow (in a generated project)

1. Drop knowledge into `resource/`.
2. Run `/sprint-start "your goal"` — this also creates a `sprint/<slug>` git branch for the sprint.
3. The Planner drafts `sprints/<date>_<slug>/plan.md` — review and approve.
4. Specialists execute tasks; each appends to its work-log.
5. Run `/sprint-close` — the Reviewer writes the Sprint Closeout.
6. Repeat.

See `CLAUDE.md` inside any generated project for the full workflow.

## Sprint board (offline kanban)

Each scaffolded project includes a self-contained kanban view of the active sprint. From inside the project, run:

    python3 .claude/scripts/board.py

This writes `sprint-board.html` at the project root and opens it in your browser. The HTML inlines all CSS/JS — no network access needed. Re-run the script (or `/sprint-board` inside Claude Code) any time to refresh. With no active sprint, the board renders an empty state.

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
to `fixes/<YYYY-MM-DD>_<slug>.md`. No planner, reviewer, branch, or approval gates.

## Agent roster

Core (always installed): `planner`, `reviewer`.

Specialists (installed via wizard or `--add-agent`):
- `researcher`, `architect`, `implementer`,
- `backend-specialist`, `frontend-specialist`, `qa-engineer`,
- `devops`, `documenter`,
- `data-ml-engineer`, `security-reviewer`.

## Bundled skills

The template vendors 12 superpowers skills into `.claude/skills/`:
`test-driven-development`, `systematic-debugging`, `verification-before-completion`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `dispatching-parallel-agents`, `requesting-code-review`, `receiving-code-review`, `brainstorming`, `frontend-design`, `finishing-a-development-branch`.

The template also bundles one custom project skill, `using-git`, which defines the
commit-attribution convention agents follow.

## Obsidian knowledge-vault module (opt-in)

An opt-in module adds an Obsidian-backed **knowledge vault** at `wiki/` — the
team's shared, durable memory — plus the skills, agents, commands, and hooks that
operate it. It is **off by default**; without it, a scaffolded project is
byte-for-byte identical to today.

Enable it at scaffold time with `--with-obsidian` (the interactive wizard also
asks a yes/no question, default no), or add it to an existing project in place:

```bash
# at scaffold time
python3 setup.py /path/to/new-project --with-obsidian

# in place, on an already-scaffolded project (idempotent)
python3 .claude/scripts/team_setup.py --add-obsidian
```

When enabled, the module adds:

- **Skills / commands:** `/wiki` (ingest a source, query, lint), `/save` (persist
  a note or sprint closeout), `/canvas` (visual board) — plus `defuddle`, `think`,
  `obsidian-markdown`, `obsidian-bases`.
- **Agents:** `verifier`, `wiki-ingest`, `wiki-lint`.
- **Vault seed:** a ready-to-use `wiki/` skeleton (`index.md`, `hot.md`, `log.md`,
  `overview.md` and the `concepts/ entities/ sources/ questions/ comparisons/`
  folders) — usable immediately, no Obsidian desktop app required.
- **Hooks** (merged into `.claude/settings.json`): load `wiki/hot.md` on session
  start, reload it after context compaction, and prompt to update it when the
  vault changed. There is **no** auto-commit hook — the vault is committed through
  the normal sprint-branch + `@<nickname>:` flow like any other change.
- **Permissions** for the vault scripts, and `.vault-meta/` (runtime locks/caches)
  added to the project `.gitignore`.

The generated team becomes vault-aware: the Researcher ingests/queries the vault,
the Reviewer `/save`s sprint closeouts into it, and the Planner/Implementer check
it for prior decisions before starting.

If you have the Obsidian desktop app, run the optional setup script once to wire
up the app's vault config:

```bash
.claude/scripts/setup-vault.sh
```

The module is a curated subset of the MIT-licensed `claude-obsidian` project; see
`template/optional/obsidian/ATTRIBUTION.md` for provenance and exactly what was
and was not vendored.

## Manual smoke test (run before tagging a release)

```bash
# 1. Scaffold a fresh project.
rm -rf /tmp/team-ai-smoketest
python3 setup.py /tmp/team-ai-smoketest --minimal

# 2. Open it in Claude Code.
cd /tmp/team-ai-smoketest

# 3. Inside Claude Code, run:
#    /sprint-start "create a hello world Python script in src/"
#
# 4. Verify:
#    - sprints/.active is created
#    - sprints/<date>_create-a-hello-world.../plan.md is written
#    - planner is dispatched and the guide approval gate hits
#    - on approval, specialists run and work-logs/<nickname>.md gets entries
#    - /sprint-close triggers the reviewer; Sprint Closeout is PASS
#    - sprints/.active is removed
#    - src/hello.py exists and runs
```

## Requirements

Python 3.8+. Standard library only. (Use `python3` on macOS/Linux where `python` is unavailable.)

## Tests

```bash
python3 -m unittest discover -s tests -v
```
