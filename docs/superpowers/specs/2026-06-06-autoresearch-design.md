# Autoresearch Skill — Design Spec

**Date:** 2026-06-06
**Branch:** feat/obsidian-module
**Status:** Approved

---

## Goal

Vendor the `autoresearch` skill from `claude-obsidian-ref` into the team-ai Obsidian module, making it available as an 11th skill in any project scaffolded with `--with-obsidian`.

---

## Scope

Content-only change — no `setup.py` modifications required. `apply_obsidian_module` already copies `skills/` via `copytree` and `wiki-seed/` via `rglob` generically; new files are picked up automatically.

| Action | File |
|--------|------|
| New | `template/optional/obsidian/skills/autoresearch/SKILL.md` |
| New | `template/optional/obsidian/wiki-seed/references/program.md` |
| Updated | `template/optional/obsidian/snippets/claude-section.md` |
| Updated | `template/optional/obsidian/snippets/researcher.md` |
| Updated | `template/optional/obsidian/ATTRIBUTION.md` |
| Updated | `tests/test_obsidian_module.py` |

---

## Placement

Autoresearch is part of the Obsidian module only — it requires the vault (`wiki/`) to exist and is not available to projects scaffolded without `--with-obsidian`. It is a standalone skill invoked directly via `/autoresearch [topic]`; the existing researcher agent is unchanged.

---

## Skill Trimming

Source: `claude-obsidian-ref/skills/autoresearch/SKILL.md`

### Removed

- **Transport section** — wiki-cli / mcp-obsidian / mcpvault decision tree. Replaced with one line: filesystem `Write` tool is the transport; `.claude/scripts/detect-transport.sh` is available as a fallback check.
- **Mode awareness section** — entire `wiki-mode.py route` block. All output paths become fixed: `wiki/sources/`, `wiki/concepts/`, `wiki/entities/`, `wiki/questions/`.
- **Topic Selection Section B** — DragonScale "boundary-first selection" (`boundary-score.py`, frontier surfacing). Removed entirely. Two topic paths remain: explicit topic from user (A), or ask the user (C).

### Rewritten

- `scripts/wiki-lock.sh` → `.claude/scripts/wiki-lock.sh`
- `scripts/detect-transport.sh` → `.claude/scripts/detect-transport.sh`
- `references/program.md` → `wiki/references/program.md`

### Kept intact

- Core 3-round research loop (broad search → gap fill → synthesis check)
- Web egress hygiene section (URL validation, content sanitization — security-relevant)
- Concurrency / wiki-lock section
- Filing structure (sources / concepts / entities / questions)
- Synthesis page template and structure
- After Filing section (index, log, hot.md updates)
- `think` skill mapping table
- Constraints section (reads `wiki/references/program.md`)
- Report to User format

---

## wiki-seed: references/program.md

`claude-obsidian-ref/skills/autoresearch/references/program.md` is vendored verbatim to `template/optional/obsidian/wiki-seed/references/program.md`.

At scaffold time this lands at `wiki/references/program.md` — user-editable vault config. The file contains no dropped-feature references and is clean to vendor as-is.

The `wiki-seed/references/` subdirectory is new. `apply_obsidian_module`'s existing `rglob` loop creates parent directories automatically; no code change needed.

---

## Snippet Updates

**`snippets/claude-section.md`** — add inside the `<!-- obsidian:module:start/end -->` block, appended to the command list:

```
- `/autoresearch` — autonomous multi-round research loop; findings filed directly into the vault.
```

**`snippets/researcher.md`** — add inside the `<!-- obsidian:module:start/end -->` block, after the ingest/query bullets:

```
- For deep, autonomous research, invoke `/autoresearch [topic]` — it runs the loop independently and files everything into the vault.
```

The other three snippets (`reviewer.md`, `planner-implementer.md`, `team.md`) are unchanged — autoresearch is a research-phase tool.

Updates flow through both paths: new `--with-obsidian` scaffolds render updated snippets into templates; `--add-obsidian` injects updated blocks (idempotent marker prevents double-injection).

---

## ATTRIBUTION.md Update

Move `autoresearch` from the "What was NOT vendored" list to the "What was vendored" list under Skills.

---

## Tests

Changes to `tests/test_obsidian_module.py`:

1. **`test_skills_commands_agents_present`** — add `"autoresearch"` to the skills list.
2. **New `test_program_md_in_wiki`** in `TestObsidianEnabled` — assert `wiki/references/program.md` exists after a `--with-obsidian` scaffold.

Verification grep note: the existing Task 2 dropped-feature grep checks all skills for the string `autoresearch`. After this change the grep must exclude the `autoresearch/` skill dir itself. The new implementation plan's verification step handles this.

---

## What This Is Not

- No new agent (the researcher agent is unchanged)
- No new command (the skill's own trigger `/autoresearch` is sufficient)
- No new hook
- No setup.py changes
- No changes to the 5 existing wiki-seed pages
