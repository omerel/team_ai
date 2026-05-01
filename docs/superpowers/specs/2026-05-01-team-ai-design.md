# Team-AI Multi-Agent Framework — Design Spec

**Date:** 2026-05-01
**Status:** Approved (brainstorming complete; ready for implementation plan)

## 1. Goal

Build a reusable `.claude/` template plus a Python setup script (`setup.py`) that scaffolds a multi-agent project workspace into any directory. The user (the "guide") drives work via sprints. A team of subagents — Planner, Reviewer, and a configurable set of specialists — execute each sprint under the coordination of an Orchestrator (the main Claude Code session). All state lives in plain files, so any sprint can be paused, inspected, or resumed without external infrastructure.

The template must work for any kind of technological project — software, research, product work — without modification.

## 2. Architecture

Three layers, kept strictly separate:

1. **Knowledge layer** — `resource/` (user-curated facts) and `CLAUDE.md` (workflow rules every agent reads). Read by agents, written only by humans.
2. **Coordination layer** — `sprints/<sprint>/plan.md` (the contract for the sprint) and `sprints/<sprint>/work-logs/*.md` (per-agent execution trail). Read and written by agents during execution.
3. **Execution layer** — `src/` (the actual project deliverable).

**Stateless invocation principle:** every agent dispatch is one-shot and stateless. The plan, work-logs, and resources are the only memory. A sprint can resume after any interruption because the Orchestrator can reconstruct full state from these files alone.

**The Orchestrator is the main Claude session reading `CLAUDE.md`** — it is *not* a separate dispatchable agent. Every other team member (Planner, Reviewer, specialists) is a real subagent file in `.claude/agents/` dispatched via the Task tool.

## 3. Agent Roster

Each agent is a markdown file in `.claude/agents/<role>.md` with frontmatter (`name`, `description`, `tools`) plus a body that defines responsibilities, the bundled skills it must invoke, and the I/O contract.

### Core agents (always installed)

- **`planner`** — Reads sprint goal, `resource/`, `team.md`, and `CLAUDE.md`. Produces `plan.md` with task list, per-task specialist assignment (by nickname), and acceptance criteria. Skills: `writing-plans`, `brainstorming`.
- **`reviewer`** — Independent QA gate. Verifies each completed task meets its acceptance criteria. Writes the `Sprint Closeout` section in `plan.md`. Skills: `verification-before-completion`, `requesting-code-review`, `receiving-code-review`, `finishing-a-development-branch`.

### Specialists (interactive setup picks which to install)

- **`researcher`** — Reads `resource/` and external info, synthesizes findings. Skills: `brainstorming`.
- **`architect`** — System design, tech-stack choices, file-structure decisions. Skills: `brainstorming`, `writing-plans`.
- **`implementer`** — Generic builder; default executor for code tasks not claimed by a specialist. Skills: `test-driven-development`, `systematic-debugging`, `receiving-code-review`.
- **`backend-specialist`** — APIs, services, data layer. Same skills as Implementer.
- **`frontend-specialist`** — UI/UX implementation. Skills: `frontend-design`, `test-driven-development`, `systematic-debugging`.
- **`qa-engineer`** — Writes and runs tests, validates behavior. Skills: `test-driven-development`, `systematic-debugging`, `verification-before-completion`.
- **`devops`** — CI/CD, deployment, infra. Skills: `verification-before-completion`.
- **`documenter`** — READMEs, API docs, user guides.
- **`data-ml-engineer`** *(optional)* — Data pipelines, ML models. Skills: `test-driven-development`, `systematic-debugging`.
- **`security-reviewer`** *(optional)* — Security audit. Skills: `verification-before-completion`.

### Nicknames

Every installed agent is assigned a nickname during setup. Defaults to the role name; the wizard lets the user customize. Rules:
- File location stays role-based for stability: `.claude/agents/backend-specialist.md`.
- Frontmatter `name:` is set to the **nickname** — this is the dispatch identifier (`subagent_type: "rocky"`).
- Prompt body addresses the agent in first person by nickname ("You are Rocky, the team's backend specialist...").
- Work-log filenames use nicknames: `work-logs/rocky.md`.
- `plan.md` task assignments reference nicknames: `Task 3: build /login endpoint → @rocky`.
- Nicknames must be unique within the team, lowercase, regex `^[a-z][a-z0-9-]{1,30}$`, and must not collide with reserved subagent names (`general-purpose`, `Explore`, etc.).
- A team roster file `.claude/team.md` lists `nickname → official role → one-line description`. Both Orchestrator and Planner read this at sprint start.
- Renames happen via `python .claude/scripts/team_setup.py --rename old=new`, which updates frontmatter `name`, prompt body references, `team.md`, and existing work-log filenames.

### Standard I/O contract (enforced by every agent's prompt)

1. Read `CLAUDE.md`, the active sprint's `plan.md`, and any relevant `resource/` files.
2. Do the assigned task.
3. Append a timestamped entry to `sprints/<active>/work-logs/<nickname>.md` with: what was attempted, what was done, what's blocked, files touched.
4. Return a one-paragraph summary to the Orchestrator.

## 4. Sprint Workflow

### Sprint definition

A sprint is a **goal-oriented work unit** — no fixed length. The user states a goal; the sprint runs plan → execute → review → close, and ends when the goal is met.

### Lifecycle

```
1. Guide runs  /sprint-start "build login flow"
        │
2. Orchestrator creates sprints/2026-05-01_login-flow/
   └─ writes sprints/.active marker
   └─ dispatches Planner
        │
3. Planner reads goal + resource/ + team.md + CLAUDE.md
   └─ writes plan.md (tasks + acceptance criteria + @nickname assignments)
        │
4. Orchestrator presents plan to guide  →  ⏸ APPROVAL GATE
        │
5. Guide approves → Orchestrator dispatches tasks in order
   └─ each specialist: read context → do work → append to work-logs/<nickname>.md → return summary
   └─ Orchestrator updates plan.md task status after each return
        │
6. All tasks done → Orchestrator runs /sprint-close (or guide does)
        │
7. Reviewer dispatched → validates against acceptance criteria
   └─ writes "Sprint Closeout" section in plan.md (PASS / FAIL + notes)
        │
8. On PASS: .active marker removed; sprint folder is now history.
   On FAIL: sprint stays open; Orchestrator dispatches fixes; rerun /sprint-close.
```

### Approval gates

Two points where the guide is in control:
1. **After plan written** — guide reviews plan, requests changes, or approves.
2. **After Reviewer writes closeout** — guide accepts close, or rejects (sprint reopens).

Everything between these gates runs autonomously unless the guide interjects.

### Slash commands (in `.claude/commands/`)

- **`/sprint-start <goal>`** — Creates the sprint folder, writes `.active`, dispatches Planner, blocks until plan approved. Refuses if `.active` already exists (unless `--force`).
- **`/sprint-status`** — Prints plan summary: % done, current task, blockers, last 3 log entries.
- **`/sprint-close`** — Dispatches Reviewer, writes Sprint Closeout. Refuses to close if any task is `pending` or `in_progress` unless guide forces.
- **`/sprint-resume`** — Reads `.active` (or most recent sprint folder by mtime if missing), summarizes state from plan + logs, asks guide to continue.

### Routing model (hybrid)

- The Planner pre-assigns specialists in `plan.md` (default path).
- The Orchestrator may re-route a task at execution time if reality differs from the plan, and **must** append a `Routing override` note to `plan.md` explaining why.
- The plan acts as a recommendation, not a contract.

### Mid-sprint handling

- **Routing override** — logged in `plan.md`.
- **Blocked task** — specialist sets task status to `blocked` with reason in plan.md and work-log; Orchestrator escalates to guide rather than guessing.
- **Guide interjections** — natural language at any time; Orchestrator treats as authoritative.
- **Reviewer FAIL** — sprint stays open; Orchestrator dispatches fixes; guide reruns `/sprint-close`.

### Status vocabulary

Plan task status uses exactly: `pending`, `in_progress`, `done`, `blocked`. No other values.

### Sprint folder naming

`sprints/<YYYY-MM-DD>_<slug>/`. The slug is derived from the goal: lowercase, alphanumeric and hyphens only, max 40 characters, generated by the Orchestrator at sprint start (e.g., goal "Build the login flow with OAuth" → slug `build-the-login-flow-with-oauth`). If the slug collides with an existing sprint folder on the same day, a numeric suffix is appended (`-2`, `-3`).

## 5. File Layout

### Generated project (output of `setup.py`)

```
my-project/
├── .claude/
│   ├── agents/                          ← only the ones the wizard installed
│   │   ├── planner.md                   ← always
│   │   ├── reviewer.md                  ← always
│   │   ├── researcher.md
│   │   ├── architect.md
│   │   ├── implementer.md
│   │   ├── backend-specialist.md
│   │   ├── frontend-specialist.md
│   │   ├── qa-engineer.md
│   │   ├── devops.md
│   │   ├── documenter.md
│   │   ├── data-ml-engineer.md          ← optional
│   │   └── security-reviewer.md         ← optional
│   ├── commands/
│   │   ├── sprint-start.md
│   │   ├── sprint-status.md
│   │   ├── sprint-close.md
│   │   └── sprint-resume.md
│   ├── skills/                          ← vendored copies of superpowers skills
│   │   ├── test-driven-development/
│   │   ├── systematic-debugging/
│   │   ├── verification-before-completion/
│   │   ├── writing-plans/
│   │   ├── executing-plans/
│   │   ├── subagent-driven-development/
│   │   ├── dispatching-parallel-agents/
│   │   ├── requesting-code-review/
│   │   ├── receiving-code-review/
│   │   ├── brainstorming/
│   │   ├── frontend-design/
│   │   └── finishing-a-development-branch/
│   ├── scripts/
│   │   └── team_setup.py                ← copy of setup.py for in-project ops
│   ├── team.md                          ← nickname → role roster
│   └── settings.json                    ← minimal perms; any hooks
├── CLAUDE.md                            ← workflow doc, loaded by every agent
├── resource/                            ← flat user-curated knowledge
│   └── README.md                        ← short stub explaining the folder
├── sprints/
│   ├── .active                          ← marker file (only when a sprint is open)
│   └── <date>_<slug>/
│       ├── plan.md
│       └── work-logs/
│           └── <nickname>.md
└── src/                                 ← the deliverable
```

### Template repo (where the scaffolder lives)

```
team-ai-template/
├── setup.py                             ← scaffolder + in-place tools
├── template/                            ← raw template files copied during scaffold
│   ├── claude/                          ← becomes .claude/ in the target
│   │   ├── agents/                      ← every agent .md.tmpl
│   │   ├── commands/
│   │   ├── skills/                      ← vendored skill source files
│   │   ├── team.md.tmpl
│   │   └── settings.json
│   ├── CLAUDE.md.tmpl
│   └── resource_README.md
├── tests/                               ← unittest tests for the script
└── README.md                            ← how to use the template
```

### Resource folder

Flat layout. User drops any files (PDFs, markdown, links, datasets) directly into `resource/`. Every agent's prompt instructs it to **list `resource/` first**, then **read only what's relevant** to its current task — never read the entire folder verbatim.

### `CLAUDE.md` contents

Kept tight. Six sections:
1. Workflow rules — sprints, slash commands, approval gates.
2. Agent dispatch protocol — Orchestrator's responsibility, how to read `team.md`, hybrid routing rule.
3. I/O contract — every agent appends to its work-log before returning.
4. Resource rule — list `resource/` first, read what's relevant; never assume contents.
5. Sprint file conventions — paths, status vocabulary, how to update `plan.md`.
6. Pointer to `.claude/team.md`.

Detailed agent behavior lives in each agent's prompt, not in `CLAUDE.md`.

## 6. Setup Script (`setup.py`)

### Modes

```bash
# Bootstrap a new project (interactive wizard — default)
python setup.py /path/to/new-project

# Bootstrap with all defaults, no prompts
python setup.py /path/to/new-project --minimal

# In-place ops (run from inside the generated project)
python .claude/scripts/team_setup.py --rename rocky=ricky
python .claude/scripts/team_setup.py --add-agent security-reviewer
python .claude/scripts/team_setup.py --remove-agent data-ml-engineer
python .claude/scripts/team_setup.py --list-team
```

### Wizard flow

1. **Project info** — name (default: target dir basename), one-line description.
2. **Specialist selection** — for each optional agent (every specialist except `planner` and `reviewer`), ask y/N.
3. **Nicknames** — for each installed agent, prompt with role-name default; user can keep or override.
4. **Confirmation** — print roster summary, ask to proceed.

### `--minimal` defaults

- Project name = target dir basename.
- Empty description.
- Install: `planner`, `reviewer`, `researcher`, `architect`, `implementer`, `qa-engineer`, `documenter`. Skip the heavy specialists (`backend-specialist`, `frontend-specialist`, `devops`, `data-ml-engineer`, `security-reviewer`) — user can add later.
- Nicknames = role names.

### What the script does, in order

1. Validate target path doesn't already contain `.claude/` (unless `--force`).
2. Collect inputs (wizard or defaults).
3. Validate nicknames: regex, uniqueness, no collisions with reserved subagent names.
4. Create directory tree.
5. Render templates with `string.Template` substitutions (`$project_name`, `$nickname`, `$role`, `$description`) — agent files, `CLAUDE.md`, `team.md`, `settings.json`.
6. Copy `template/claude/skills/` as-is into `.claude/skills/`.
7. Copy the script itself to `.claude/scripts/team_setup.py`.
8. Print success message and next steps.

### Error handling

Only at real boundaries:
- Target path conflict → exit with clear message + `--force` hint.
- Nickname collision in wizard → reprompt that nickname only.
- Reserved or invalid nickname → reprompt.
- Missing template files in repo → fail loudly with which file is missing.
- In-place ops on a non-generated project (no `.claude/team.md`) → exit with explanation.

### Dependencies

Standard library only. `argparse`, `pathlib`, `shutil`, `string.Template`, `re`. Python 3.8+.

## 7. Workflow-Level Error Handling

- **Planner assigns an unknown nickname** — Orchestrator validates `plan.md` assignments against `team.md` before executing. If invalid, sends the plan back to Planner with the list of valid nicknames; doesn't dispatch.
- **Specialist returns without updating its work-log** — Orchestrator detects (file unchanged, no new entry), re-dispatches the same task with an explicit "you must append to your work-log" reminder.
- **Specialist marks a task `blocked`** — Orchestrator surfaces the block to the guide rather than guessing.
- **Reviewer fails the sprint** — sprint stays open, `.active` stays in place; Orchestrator dispatches fixes; guide reruns `/sprint-close`.
- **Plan/reality contradiction** — Orchestrator never edits acceptance criteria silently. It either re-routes (with override note) or escalates to guide.

## 8. Testing

### Setup script — automated tests

Use stdlib `unittest` to keep zero deps.

- Unit: nickname validator (regex, reserved names, collisions).
- Unit: template substitution (no unrendered `$vars` in output).
- Integration: run `setup.py --minimal` against a tmpdir; assert expected file tree and key file contents.
- Integration: run `--rename` on a freshly-generated project; assert rename propagated to frontmatter `name`, prompt body, `team.md`, and existing work-log filenames.
- Integration: run `--add-agent` and `--remove-agent`; assert idempotency.

### Template & workflow — manual smoke test

Documented in the template repo's README; the template author runs this before tagging a release.

1. Generate a fresh project with `--minimal`.
2. Open it in Claude Code; run `/sprint-start "create a hello world Python script in src/"`.
3. Verify: plan written, guide approval gate hits, specialists dispatched, work-logs populated, Reviewer closes, `.active` removed, `src/hello.py` exists.

## 9. Out of Scope (YAGNI)

- No web UI, no dashboard, no database. Files only.
- No telemetry or analytics.
- No automatic retry/backoff loops — failures escalate to the guide.
- No concurrent sprint support — one active sprint at a time.
- No version pinning of bundled skills (vendored copies are whatever shipped with the template; updates happen by re-running setup).
- No automated end-to-end test of the live Claude Code workflow — that's the manual smoke test.
