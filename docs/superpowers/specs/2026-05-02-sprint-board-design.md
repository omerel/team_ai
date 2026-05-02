# Sprint Board — Design

**Date:** 2026-05-02
**Status:** Approved (verbally) — visual preview at repo root accepted

## Goal

Give every scaffolded team-ai project a single command that produces an offline, self-contained HTML kanban view of the active sprint. The user runs the command (or the `/sprint-board` slash command) and a `sprint-board.html` opens in their browser, rendering tasks from the live `plan.md` as a four-column kanban.

## Non-goals

- No live reload or file watching — refresh by re-running the generator.
- No editing from the board (read-only view).
- No history view across closed sprints.
- No build step, package install, or network access.

## Constraints

- Pure Python 3.8+ stdlib (matches existing `setup.py`).
- Generated HTML must work under `file://` with no external CSS, JS, fonts, or images.
- Must degrade gracefully when there is no active sprint.

## Architecture

A generator script reads sprint state from disk and emits a single self-contained HTML file. The HTML embeds the parsed sprint as a JSON object inside an inline `<script>` tag; rendering is done client-side by inline JS. CSS is inline in `<style>`.

### Inputs

- `sprints/.active` — file containing the active sprint folder name (single line). Optional: if missing or empty, the board renders an empty state.
- `sprints/<active>/plan.md` — source of tasks; structure defined in `CLAUDE.md` §5.
- `.claude/team.md` — `@nickname → role` map, used to show a role tooltip on each card's assignee chip.

### Output

- `<project>/sprint-board.html` — overwritten on each run.

### Components

1. **`board.py` (new)** — `template/claude/scripts/board.py`
   - Locates the project root: `cwd` if `.claude/team.md` exists there, else walks up until found, else exits with a clear error.
   - Reads `sprints/.active` (tolerates missing/empty file).
   - Parses the active `plan.md` into a `Sprint` dict.
   - Parses `.claude/team.md` into a `{nickname: role}` map.
   - Renders the HTML by substituting `__SPRINT_DATA__` in a template string with `json.dumps(sprint)` and writing the result.
   - Calls `webbrowser.open()` on the output path unless `--no-open` is passed.

2. **`sprint-board.template.html` (new)** — `template/claude/scripts/sprint-board.template.html`
   - The HTML/CSS/JS shell. Contains a single sentinel comment that `board.py` replaces with the JSON payload:
     ```js
     const SPRINT = /*__SPRINT_DATA__*/ null;
     ```
   - Visual design and rendering JS already proven by `sprint-board.html` at the repo root.

3. **`/sprint-board` slash command (new)** — `template/claude/commands/sprint-board.md`
   - One step: run `python3 .claude/scripts/board.py` and surface the output path.

4. **Scaffolder integration** — `setup.py`
   - During `scaffold_project`, copy `board.py` and `sprint-board.template.html` into `<project>/.claude/scripts/`, and the slash command into `<project>/.claude/commands/`.
   - The generated `sprint-board.html` is an output artifact, but generated projects don't have a managed `.gitignore` today — leaving it untracked is the user's call.

5. **Repo-root preview** — the `sprint-board.html` already at the repo root is the visual contract. It stays tracked as a design artifact and is unaffected by the generator (the generator only runs inside scaffolded child projects, never on the meta-repo).

### Data shape

The embedded JSON has this shape:

```json
{
  "project_name": "string",
  "folder": "2026-05-02_<slug>",
  "goal": "string",
  "started": "YYYY-MM-DD",
  "team": { "nickname": "role" },
  "tasks": [
    {
      "id": "T1",
      "status": "pending|in_progress|done|blocked",
      "assignee": "nickname",
      "desc": "string",
      "acceptance": "string | null",
      "notes": "string | null"
    }
  ]
}
```

When there is no active sprint, the JSON is:
```json
{ "project_name": "<name>", "folder": null, "goal": null, "started": null, "team": {}, "tasks": [] }
```
and the HTML shows an empty-state message with the four columns still drawn.

## plan.md parser

Inputs span lines like:

```
- [ ] **T1** [in_progress] @backend — Implement the parser.
  - Acceptance: every status renders.
  - Notes: tolerate missing acceptance.
```

Strategy:
- Locate the `## Tasks` section; stop at the next `^## ` heading.
- For each top-level bullet beginning with `- [ ]` or `- [x]`:
  - Extract `**T<id>**`, the `[status]` token, the `@nickname`, and the description after `—` (em dash) or `--`.
  - Read indented sub-bullets until the next top-level bullet; capture `Acceptance:` and `Notes:` (case-insensitive prefix).
- Tolerate the em dash `—`, an ASCII `-`, or `--` between assignee and description.
- Skip bullets that fail to match the task pattern (don't abort).

Header parsing:
- `# Sprint: <goal>` → goal
- `**Started:** <date>` → started

## Visual style (locked in by preview)

Reuse the layout, palette, and component styles from the approved `sprint-board.html` preview:
- Dark theme with subtle radial-gradient backdrop
- Four columns with colored top accent bars and count chips
- Cards: task-ID mono pill, hashed-color assignee avatar + chip, description, Acceptance + Notes labels, red side-accent + "Blocked" tag for blocked tasks
- Responsive: 4 cols → 2 cols → 1 col

## Error handling

- Missing `.claude/team.md` → exit with `error: not a team-ai project (no .claude/team.md)`.
- Missing `sprints/` → render empty-state HTML (this is a fresh project).
- Missing `sprints/.active` or pointing to a non-existent folder → render empty-state HTML.
- Malformed `plan.md` (no `## Tasks` section) → render header + empty columns; do not crash.
- `--no-open` skips `webbrowser.open` (useful for CI / tests).

## Testing

Add a test module `tests/test_board.py`:
- `test_parse_plan_full` — a fixture plan.md with one task in each status, with and without acceptance/notes.
- `test_parse_plan_empty` — `## Tasks` exists but is empty.
- `test_parse_plan_missing_tasks_section` — header only.
- `test_render_writes_self_contained_html` — generated output contains no `http://` / `https://` / `src=` / `href=` references to remote assets, and embeds the JSON payload.
- `test_no_active_sprint` — generator runs without a `.active` file and emits the empty-state HTML.
- `test_team_map_parsing` — reuses the team.md parser style already in `setup.py`.

Run via the existing `python3 -m unittest discover -s tests -v` command. No new dependencies.

## Open questions resolved

- **Approach:** Generator script + self-contained HTML (option A), confirmed.
- **Columns:** Four (Pending, In Progress, Done, Blocked), confirmed.
- **Visual:** The repo-root preview is the locked-in design.
