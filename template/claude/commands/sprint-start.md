---
description: Start a new sprint with a goal
argument-hint: "<goal>"
---

Start a new sprint with goal: $ARGUMENTS

Steps:
1. Check for an active sprint by looking for `sprints/.active`. If it exists, refuse and tell the guide to close the current sprint first (or to pass `--force` if they really mean it).
2. Generate the sprint slug from the goal: lowercase, `[a-z0-9-]` only, max 40 chars (see `CLAUDE.md` §5). If a folder of the same date+slug exists, append `-2`, `-3`, etc.
3. Create `sprints/<YYYY-MM-DD>_<slug>/`, plus `sprints/<YYYY-MM-DD>_<slug>/work-logs/` empty.
4. Write the folder name into `sprints/.active` (single line, no trailing newline).
5. Read `.claude/team.md` so you know which nicknames are valid.
6. Dispatch the **planner** subagent with this prompt:
   - "Sprint goal: <goal>. Read CLAUDE.md, team.md, and resource/. Write sprints/<folder>/plan.md following the structure in CLAUDE.md §5. Assign each task to a teammate by @nickname (use only nicknames from team.md). Return when plan.md is written."
7. After the planner returns, present the plan summary to the guide and pause for approval. Do not dispatch any other agent until the guide approves.
