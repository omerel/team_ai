# Obsidian Knowledge-Vault Module for team-ai

**Date:** 2026-06-03
**Status:** Approved design
**Author:** @elomer (with Claude)

## Summary

Integrate the curated core of the `claude-obsidian` plugin into the `team-ai`
scaffolder as an **opt-in module**. When enabled, a scaffolded project gains an
Obsidian-backed knowledge vault — skills, slash commands, agents, hooks, and note
templates — and the generated team's workflow, agents, and `CLAUDE.md` become
aware of and actively use the vault as shared team memory. When disabled (the
default), the scaffolded project is byte-for-byte identical to today.

Source repo: `claude-obsidian` (MIT licensed). Only a curated subset is vendored.

## Goals

- Opt-in: off by default, enabled via a CLI flag or wizard question at scaffold
  time, and addable to an existing project in-place.
- Curated core only — no heavy dependencies (no Python retrieval pipeline, no
  ollama, no API egress, no DragonScale, no benchmark/test harness).
- The scaffolded team's agents actively use the vault (researcher ingests/queries,
  reviewer saves closeouts), not just expose standalone tools.
- Vault git activity flows through team-ai's existing sprint-branch +
  `@<nickname>:` commit convention — no competing auto-commit path.
- Default scaffold output unchanged; all existing tests still pass.
- MIT attribution preserved.

## Non-Goals

- The Obsidian retrieval pipeline (`wiki-retrieve`: BM25 / rerank / contextual-
  prefix), `wiki-cli` transport layer, `wiki-mode` methodology modes, `wiki-fold`
  / DragonScale, and `autoresearch` are **not** vendored in this iteration.
- The plugin's `PostToolUse` auto-commit hook is not vendored.
- Auto-running `setup-vault.sh` (it requires the Obsidian desktop app).

## Architecture: staging directory + scaffold-time merge

team-ai copies `template/claude/` wholesale into a project's `.claude/` and
renders `.tmpl` files with plain `string.Template` substitution (no conditionals).
To keep the module off by default, it lives **outside** the always-copied tree
and is merged in only when enabled.

```
template/
  optional/
    obsidian/
      skills/        # 10 curated SKILL.md dirs
      agents/        # verifier, wiki-ingest, wiki-lint
      commands/      # wiki.md, save.md, canvas.md
      hooks/         # hooks.json (SessionStart, PostCompact, Stop only)
      scripts/       # only scripts the kept skills require
      templates/     # 5 Obsidian note templates (_templates)
      wiki-seed/     # minimal wiki/ skeleton dropped at project root
      snippets/      # awareness blocks injected into rendered .tmpl files
        claude-section.md
        researcher.md
        reviewer.md
        planner-implementer.md
        team.md
      permissions.json   # extra settings.json permissions to merge
      LICENSE            # vendored MIT license from claude-obsidian
      ATTRIBUTION.md     # provenance + what was/wasn't vendored
```

When the module is enabled, `setup.py`:
1. Merges `skills/ agents/ commands/ hooks/ scripts/ templates/` into the target
   `.claude/`.
2. Drops `wiki-seed/` as `wiki/` at the project root.
3. Merges `permissions.json` entries into the rendered `settings.json`.
4. Fills the `$obsidian_*` template variables from `snippets/`.

When disabled, the `$obsidian_*` variables render to empty strings and nothing
Obsidian-related is copied. The default tree stays byte-for-byte identical.

## Curated component inventory

**Skills (10):** `wiki`, `wiki-ingest`, `wiki-query`, `wiki-lint`, `save`,
`canvas`, `defuddle`, `think`, `obsidian-markdown`, `obsidian-bases`.

Dropped skills: `wiki-retrieve`, `wiki-cli`, `wiki-mode`, `wiki-fold`,
`autoresearch`. The kept skills have filesystem fallbacks for the dropped opt-in
features; implementation must trim any now-dangling references so no skill points
at a missing script.

**Commands (3):** `/wiki`, `/save`, `/canvas`. (`/autoresearch` dropped.)

**Agents (3):** `verifier`, `wiki-ingest`, `wiki-lint`.

**Hooks:** keep `SessionStart` + `PostCompact` (load/reload `hot.md`) and the
`Stop` "update hot.md" prompt. Drop the `PostToolUse` auto-commit hook.

**Templates:** the 5 Obsidian note templates (`source`, `entity`, `concept`,
`question`, `comparison`).

**Scripts:** the lightweight scripts the kept skills require — `detect-transport.sh`
and `wiki-lock.sh` (multi-writer locking is kept). The full set is finalized during
planning by grepping the kept skills for script references and pulling in whatever
they reference.

**Vault seed:** minimal `wiki/` skeleton (`index.md`, `hot.md`, `log.md`,
`overview.md`, and the `concepts/ entities/ sources/ questions/ comparisons/`
folders) so ingest/query work immediately without the Obsidian desktop app.

**Setup:** a trimmed `setup-vault.sh` shipped under `.claude/scripts/`, run on
demand (documented), to configure the actual Obsidian app for users who have it.

## Scaffolder wiring (`setup.py`)

- New `--with-obsidian` CLI flag.
- New wizard yes/no question, default **no**.
- An `apply_obsidian_module(target)` step performing the 4 merge actions above.
- The relevant `.tmpl` files gain `$obsidian_*` placeholders; the render mapping
  always supplies them (snippet content when enabled, `""` when not), so
  `string.Template` never errors on a missing key.

### In-place installer

- New `--add-obsidian` in-place op (sibling of `--add-agent` / `--remove-agent`)
  that applies the same merge to an already-scaffolded project: copies the module,
  merges `settings.json` permissions, and injects the awareness blocks into the
  existing rendered `CLAUDE.md` and agent files. Idempotent / safe to re-run.

## Awareness wiring (injected only when enabled)

- **`CLAUDE.md.tmpl`** (`$obsidian_section`): a "Knowledge Vault" section — vault
  is shared team memory; lists `/wiki` `/save` `/canvas`; instructs agents to
  query the vault for prior context; references the `using-git` attribution
  convention for vault commits.
- **`researcher.md.tmpl`** (`$obsidian_researcher`): ingest sources via
  `wiki-ingest` and query via `wiki-query` instead of re-reading raw files.
- **`reviewer.md.tmpl`** (`$obsidian_reviewer`): `/save` the sprint closeout into
  the vault as durable memory.
- **`planner.md.tmpl` / `implementer.md.tmpl`** (`$obsidian_section` light line):
  check the vault for relevant prior decisions before starting.
- **`team.md.tmpl`**: note the vault as shared memory.

## Git & version control

- No auto-commit hook. Vault files are committed by agents through the normal
  sprint flow: `@<nickname>:` messages on the `sprint/<slug>` branch, merged via
  `/sprint-close` + `finishing-a-development-branch` like any other change.
- `wiki/` is tracked (durable team memory). `.vault-meta/` runtime artifacts
  (locks, caches, logs) are added to the project `.gitignore`.
- The kept hooks are non-git and only touch `hot.md`; they coexist cleanly.

## Vault initialization

- The `wiki/` seed makes the vault usable immediately, no desktop app required.
- `setup-vault.sh` is run on demand; the scaffolder prints a one-line notice when
  the module is added: "Obsidian module added — run
  `.claude/scripts/setup-vault.sh` to wire up the Obsidian app."
- No new install-time dependencies for the curated core.

## Testing

New `tests/test_obsidian_module.py`:
- **Enabled:** `--with-obsidian` scaffold contains the expected
  skills/commands/agents/hooks/templates and the `wiki/` seed; `CLAUDE.md` has the
  vault section; `settings.json` has the extra permissions; the auto-commit hook
  is **absent**.
- **Disabled (default):** no Obsidian artifacts present; no leftover `$obsidian_*`
  placeholders in any rendered file; default tree unchanged.
- **In-place:** `--add-obsidian` on a plain scaffold produces the same result as
  scaffolding with `--with-obsidian`, and is idempotent.

All existing 12 tests must still pass — the byte-for-byte-identical default tree
is the primary guard.

## Documentation

- `README.md`: document the `--with-obsidian` flag, the `--add-obsidian` in-place
  op, what the module adds, and the optional `setup-vault.sh` step.
- This spec committed to
  `docs/superpowers/specs/2026-06-03-obsidian-module-design.md`.

## Licensing

claude-obsidian is MIT. Vendor its `LICENSE` and an `ATTRIBUTION.md` (provenance,
upstream repo, and what was / was not vendored) under `template/optional/obsidian/`.

## Open questions / risks

- Exact script dependency set of the kept skills — resolved during planning by
  grepping kept skills for `scripts/` references; trim dangling references to the
  *dropped* opt-in features only (`wiki-lock.sh` and `detect-transport.sh` are kept).
- `verifier` agent is vendored as-is, including its Obsidian-specific "six-cut"
  audit kernel.
- `settings.json` permission merge must dedupe against existing entries.
