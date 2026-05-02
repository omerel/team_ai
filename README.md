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
```

## In-place operations

After a project is generated, run these from inside it (or pass the project path as the first argument):

```bash
python3 .claude/scripts/team_setup.py --list-team
python3 .claude/scripts/team_setup.py --rename rocky=ricky
python3 .claude/scripts/team_setup.py --add-agent backend-specialist
python3 .claude/scripts/team_setup.py --add-agent backend-specialist=rocky
python3 .claude/scripts/team_setup.py --remove-agent rocky
```

## Sprint workflow (in a generated project)

1. Drop knowledge into `resource/`.
2. Run `/sprint-start "your goal"`.
3. The Planner drafts `sprints/<date>_<slug>/plan.md` — review and approve.
4. Specialists execute tasks; each appends to its work-log.
5. Run `/sprint-close` — the Reviewer writes the Sprint Closeout.
6. Repeat.

See `CLAUDE.md` inside any generated project for the full workflow.

## Sprint board (offline kanban)

Each scaffolded project includes a self-contained kanban view of the active sprint. From inside the project, run:

    python3 .claude/scripts/board.py

This writes `sprint-board.html` at the project root and opens it in your browser. The HTML inlines all CSS/JS — no network access needed. Re-run the script (or `/sprint-board` inside Claude Code) any time to refresh. With no active sprint, the board renders an empty state.

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
