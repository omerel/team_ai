# Obsidian Knowledge-Vault Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in Obsidian knowledge-vault module to the team-ai scaffolder that, when enabled, gives a scaffolded project a curated Obsidian-backed vault (skills, agents, commands, hooks, templates, seed) and makes the generated team aware of it — while keeping the default scaffold output byte-for-byte identical.

**Architecture:** The module lives outside the always-copied `template/claude/` tree, under `template/optional/obsidian/`, vendored from the MIT-licensed `claude-obsidian` repo (local ref at `/home/omer/Projects/claude-obsidian-ref`). `setup.py` gains a `--with-obsidian` flag and a wizard question (default no); when enabled it merges the module into the target `.claude/`, drops a minimal `wiki/` seed at the project root, merges extra permissions + the 3 kept hooks into `settings.json`, and fills `$obsidian_*` template variables from `snippets/`. When disabled, those variables render to empty strings and nothing Obsidian-related is copied. An in-place `--add-obsidian` op applies the same merge to an already-scaffolded project, injecting marker-wrapped awareness blocks idempotently.

**Tech Stack:** Python 3 stdlib (`argparse`, `shutil`, `json`, `string.Template`, `pathlib`), `unittest`. No new runtime dependencies.

---

## Key design decisions (resolving spec gaps)

These decisions fill gaps the spec left open. They are binding for this plan.

1. **Script paths are rewritten at vendoring time.** team-ai keeps scripts under `.claude/scripts/`. The vendored skills/hooks/agents reference scripts as `scripts/<name>` (project-root relative in the source repo). All such references to the **kept** scripts (`detect-transport.sh`, `wiki-lock.sh`, `setup-vault.sh`) are rewritten to `.claude/scripts/<name>` when the file is vendored. References to **dropped** scripts/features are removed entirely. Both are baked into `template/optional/obsidian/` at authoring time — `setup.py` only ever does a mechanical copy/merge.

2. **Hooks live in `settings.json`, not a standalone file.** A standalone `.claude/hooks/hooks.json` only fires for *plugins*. A scaffolded team-ai project is not a plugin, so for the hooks to actually run they must be merged into the project `settings.json` under a `"hooks"` key. We keep the source `template/optional/obsidian/hooks/hooks.json` as the canonical definition and `setup.py` reads it and merges its `hooks` object into the rendered `settings.json`.

3. **The `PostToolUse` auto-commit hook is dropped** (per spec). Only `SessionStart`, `PostCompact`, and `Stop` are vendored. The `SessionStart` `wiki-lock.sh clear-stale` sub-command is kept (lock hygiene, non-git).

4. **Five distinct template variables, one per snippet file** (the spec's "`$obsidian_section` light line" for planner/implementer is a name collision; we use distinct names):
   - `snippets/claude-section.md`      → `$obsidian_section`     (used in `CLAUDE.md.tmpl`)
   - `snippets/researcher.md`          → `$obsidian_researcher`  (used in `researcher.md.tmpl`)
   - `snippets/reviewer.md`            → `$obsidian_reviewer`    (used in `reviewer.md.tmpl`)
   - `snippets/planner-implementer.md` → `$obsidian_note`        (used in `planner.md.tmpl` AND `implementer.md.tmpl`)
   - `snippets/team.md`                → `$obsidian_team`        (used in `team.md.tmpl`)

   All five keys are supplied to **every** `render_template` call (snippet content when enabled, `""` when disabled). `string.Template.substitute` ignores keys a template doesn't reference, so spreading all five into every mapping is safe and keeps wiring uniform.

5. **In-place injection uses marker comments for idempotency.** Each snippet is wrapped in `<!-- obsidian:module:start -->` / `<!-- obsidian:module:end -->`. The same marker-wrapped block content is what the `$obsidian_*` variables render to at scaffold time, so scaffolded and in-place-added files contain the **identical awareness block**. The two paths differ only in *placement*: at scaffold time the block lands at the template anchor (mid-file, e.g. before `## 7. Git`), while `--add-obsidian` appends it to the end of the already-rendered file — anchor-matching rendered prose would be brittle, and end-append is the robust idempotent choice. `--add-obsidian` skips injection into any file that already contains the start marker.

---

## File structure

**New static module tree** (`template/optional/obsidian/`):

```
template/optional/obsidian/
  skills/        # 10 SKILL.md dirs, vendored + trimmed
  agents/        # verifier.md, wiki-ingest.md, wiki-lint.md
  commands/      # wiki.md, save.md, canvas.md
  hooks/
    hooks.json   # SessionStart + PostCompact + Stop only; .claude/scripts paths
  scripts/       # detect-transport.sh, wiki-lock.sh, setup-vault.sh
  templates/     # _templates: source.md entity.md concept.md question.md comparison.md
  wiki-seed/     # minimal wiki/ skeleton (authored fresh, NOT copied from ref)
  snippets/      # 5 awareness blocks (authored fresh)
    claude-section.md
    researcher.md
    reviewer.md
    planner-implementer.md
    team.md
  permissions.json   # extra settings.json "allow" entries to merge
  LICENSE            # vendored MIT license
  ATTRIBUTION.md     # provenance
```

**Modified files:**
- `setup.py` — new flag, wizard question, `apply_obsidian_module`, `add_obsidian` in-place op, obsidian-var helper wired into render mappings, settings.json merge.
- `template/CLAUDE.md.tmpl` — add `$obsidian_section`.
- `template/claude/agents/researcher.md.tmpl` — add `$obsidian_researcher`.
- `template/claude/agents/reviewer.md.tmpl` — add `$obsidian_reviewer`.
- `template/claude/agents/planner.md.tmpl` — add `$obsidian_note`.
- `template/claude/agents/implementer.md.tmpl` — add `$obsidian_note`.
- `template/claude/team.md.tmpl` — add `$obsidian_team`.
- `README.md` — document the flag, the in-place op, what the module adds, the setup-vault step.

**New test file:** `tests/test_obsidian_module.py`.

---

## Task 1: Module skeleton, LICENSE, ATTRIBUTION

**Files:**
- Create: `template/optional/obsidian/LICENSE`
- Create: `template/optional/obsidian/ATTRIBUTION.md`
- Create: dir tree `template/optional/obsidian/{skills,agents,commands,hooks,scripts,templates,wiki-seed,snippets}`

- [ ] **Step 1: Create the directory skeleton**

```bash
cd /home/omer/Projects/team_ai
mkdir -p template/optional/obsidian/{skills,agents,commands,hooks,scripts,templates,wiki-seed,snippets}
```

- [ ] **Step 2: Vendor the MIT LICENSE verbatim**

```bash
cp /home/omer/Projects/claude-obsidian-ref/LICENSE template/optional/obsidian/LICENSE
```

Expected: `head -3 template/optional/obsidian/LICENSE` shows `MIT License` and the AgriciDaniel copyright line.

- [ ] **Step 3: Author ATTRIBUTION.md**

Write `template/optional/obsidian/ATTRIBUTION.md` with this exact content:

```markdown
# Attribution

The Obsidian knowledge-vault module vendored under `template/optional/obsidian/`
is a curated subset of the **claude-obsidian** project.

- **Upstream:** claude-obsidian by AgriciDaniel / AI Marketing Hub
- **License:** MIT (see `LICENSE` in this directory)
- **Underlying pattern:** the "LLM Wiki Pattern" (Andrej Karpathy)

## What was vendored

- Skills: `wiki`, `wiki-ingest`, `wiki-query`, `wiki-lint`, `save`, `canvas`,
  `defuddle`, `think`, `obsidian-markdown`, `obsidian-bases`
- Agents: `verifier`, `wiki-ingest`, `wiki-lint`
- Commands: `/wiki`, `/save`, `/canvas`
- Hooks: `SessionStart`, `PostCompact`, `Stop` (load/reload `hot.md` + lock hygiene)
- Scripts: `detect-transport.sh`, `wiki-lock.sh`, `setup-vault.sh`
- Note templates: `source`, `entity`, `concept`, `question`, `comparison`
- A minimal `wiki/` seed (authored for this module, not copied upstream)

## What was NOT vendored

- The retrieval pipeline (`wiki-retrieve`: BM25 / rerank / contextual-prefix)
- The `wiki-cli` transport layer, `wiki-mode` methodology modes
- `wiki-fold` / DragonScale, `autoresearch`
- The `PostToolUse` auto-commit hook (team-ai commits the vault through its
  normal sprint-branch + `@<nickname>:` flow instead)
- Benchmark/test harness, ollama integration, any API-egress paths

Script references and methodology hooks that pointed at the non-vendored
features were trimmed; script paths were rewritten to `.claude/scripts/`.
```

- [ ] **Step 4: Commit**

```bash
git add template/optional/obsidian/LICENSE template/optional/obsidian/ATTRIBUTION.md
git commit -m "feat: vendor Obsidian module skeleton, LICENSE, ATTRIBUTION"
```

---

## Task 2: Vendor the 10 skills (trim dropped-feature + script references)

**Files:**
- Create: `template/optional/obsidian/skills/{wiki,wiki-ingest,wiki-query,wiki-lint,save,canvas,defuddle,think,obsidian-markdown,obsidian-bases}/` (copied from ref)

The vendored skill files must contain **no** reference to a dropped feature
(`wiki-retrieve`, `wiki-cli`, `wiki-mode`, `wiki-fold`, `autoresearch`,
`DragonScale`, `ollama`, BM25, rerank, `retrieve.py`, `allocate-address.sh`,
`tiling-check.py`, `boundary-score.py`) and **no** `scripts/<name>` path except
the rewritten `.claude/scripts/{detect-transport,wiki-lock}.sh`.

- [ ] **Step 1: Copy the 10 kept skills verbatim**

```bash
cd /home/omer/Projects/team_ai
for s in wiki wiki-ingest wiki-query wiki-lint save canvas defuddle think obsidian-markdown obsidian-bases; do
  cp -r /home/omer/Projects/claude-obsidian-ref/skills/$s template/optional/obsidian/skills/$s
done
```

- [ ] **Step 2: Rewrite kept-script paths in every vendored skill**

Rewrite `scripts/detect-transport.sh` → `.claude/scripts/detect-transport.sh`
and `scripts/wiki-lock.sh` → `.claude/scripts/wiki-lock.sh` across all vendored
skills:

```bash
cd /home/omer/Projects/team_ai
grep -rl 'scripts/detect-transport.sh\|scripts/wiki-lock.sh' template/optional/obsidian/skills \
  | xargs sed -i \
      -e 's#\([^/.]\)scripts/detect-transport\.sh#\1.claude/scripts/detect-transport.sh#g' \
      -e 's#^scripts/detect-transport\.sh#.claude/scripts/detect-transport.sh#g' \
      -e 's#\([^/.]\)scripts/wiki-lock\.sh#\1.claude/scripts/wiki-lock.sh#g' \
      -e 's#^scripts/wiki-lock\.sh#.claude/scripts/wiki-lock.sh#g'
```

Then verify no `.claude/.claude/` double-prefix was introduced:

```bash
grep -rn '\.claude/\.claude/' template/optional/obsidian/skills && echo "BAD double-prefix" || echo "OK"
```

Expected: `OK`.

- [ ] **Step 3: Trim dropped-feature references skill-by-skill**

For each skill below, open the file and remove/neutralize the lines that
reference dropped features. The guiding rule: delete the dropped-feature
routing rows, fallback-detection blocks, and "see skills/<dropped>/..." links;
keep the filesystem-fallback behavior the kept skill already has. Concrete edits
(line numbers are approximate — match on content):

- `skills/wiki/SKILL.md`: delete the `AUTORESEARCH` routing-table row
  (mentions `autoresearch`) and the footer line
  `` - `/autoresearch` (after research loop finishes and pages are filed) ``.
- `skills/wiki-ingest/SKILL.md`: remove the `see skills/wiki-cli/SKILL.md` link;
  remove the `wiki-mode.py route ...` invocation lines (the page-type is chosen
  directly from the note templates instead); remove the entire
  "Address Assignment (DragonScale Mechanism 2 MVP)" section and any
  `allocate-address.sh` references; keep the `.claude/scripts/wiki-lock.sh
  acquire/release` lines and the `.claude/scripts/detect-transport.sh` line.
- `skills/wiki-query/SKILL.md`: remove the `see skills/wiki-cli/SKILL.md` link;
  remove the `wiki-retrieve` feature-detection block (`retrieve.py`,
  `.vault-meta/bm25/index.json`, `bm25_score`, `rerank_score`,
  `bin/setup-retrieve.sh`) and the CONNECT(sys) lines mentioning
  `wiki-retrieve` / `autoresearch inputs`; keep the plain-grep/filesystem query
  path as the only path; keep `.claude/scripts/detect-transport.sh`.
- `skills/wiki-lint/SKILL.md`: remove the `see skills/wiki-cli/SKILL.md` link;
  remove the DragonScale Mechanism 2/3 checks (`allocate-address.sh`,
  `tiling-check.py`, all ollama / `nomic-embed-text` / `OLLAMA_URL` lines);
  keep the orphan/dead-link/frontmatter lint checks and
  `.claude/scripts/detect-transport.sh`.
- `skills/save/SKILL.md`: remove the `see skills/wiki-cli/SKILL.md` link and the
  `wiki-mode.py route session` lines; keep `.claude/scripts/wiki-lock.sh
  acquire/release` and `.claude/scripts/detect-transport.sh`.
- `skills/canvas/SKILL.md`: remove the `` - `/autoresearch` → structured knowledge `` sub-skill line.
- `skills/think/SKILL.md`: remove the `/autoresearch` mention in the composition section.
- `skills/defuddle/SKILL.md`, `skills/obsidian-markdown/SKILL.md`,
  `skills/obsidian-bases/SKILL.md`: no dropped-feature references — leave as-is.

- [ ] **Step 4: Verify no dangling dropped-feature references remain**

```bash
cd /home/omer/Projects/team_ai
grep -rniE 'wiki-retrieve|wiki-cli|wiki-mode|wiki-fold|autoresearch|dragonscale|ollama|bm25|rerank|retrieve\.py|allocate-address|tiling-check|boundary-score|setup-retrieve' \
  template/optional/obsidian/skills && echo "FAIL: dangling reference" || echo "OK clean"
```

Expected: `OK clean`.

- [ ] **Step 5: Verify no project-root `scripts/` reference to a missing script remains**

```bash
cd /home/omer/Projects/team_ai
# Any remaining bare scripts/<x> that is not under .claude/ is a dangling ref:
grep -rnoE '(^|[^./])scripts/[A-Za-z0-9_-]+\.(sh|py)' template/optional/obsidian/skills \
  | grep -v '\.claude/scripts/' && echo "FAIL: bare scripts/ ref" || echo "OK no bare scripts refs"
```

Expected: `OK no bare scripts refs`.

- [ ] **Step 6: Commit**

```bash
git add template/optional/obsidian/skills
git commit -m "feat: vendor 10 curated Obsidian skills (trim dropped features)"
```

---

## Task 3: Vendor the 3 agents

**Files:**
- Create: `template/optional/obsidian/agents/{verifier,wiki-ingest,wiki-lint}.md`

- [ ] **Step 1: Copy the three agents verbatim**

```bash
cd /home/omer/Projects/team_ai
for a in verifier wiki-ingest wiki-lint; do
  cp /home/omer/Projects/claude-obsidian-ref/agents/$a.md template/optional/obsidian/agents/$a.md
done
```

- [ ] **Step 2: Rewrite any script path + trim dropped refs in the agents**

```bash
cd /home/omer/Projects/team_ai
grep -rl 'scripts/wiki-lock.sh\|scripts/detect-transport.sh' template/optional/obsidian/agents \
  | xargs --no-run-if-empty sed -i \
      -e 's#\([^/.]\)scripts/detect-transport\.sh#\1.claude/scripts/detect-transport.sh#g' \
      -e 's#\([^/.]\)scripts/wiki-lock\.sh#\1.claude/scripts/wiki-lock.sh#g'
```

Then open `agents/wiki-ingest.md` and `agents/wiki-lint.md` and remove any
references to `allocate-address.sh`, `tiling-check.py`, `wiki-mode`,
`.raw/.manifest.json` DragonScale steps, or ollama (the `verifier.md` "six-cut
audit kernel" is vendored **as-is** per spec — do not trim it).

- [ ] **Step 3: Verify clean**

```bash
cd /home/omer/Projects/team_ai
grep -rniE 'wiki-cli|wiki-mode|wiki-fold|autoresearch|dragonscale|ollama|allocate-address|tiling-check' \
  template/optional/obsidian/agents/wiki-ingest.md template/optional/obsidian/agents/wiki-lint.md \
  && echo "FAIL" || echo "OK clean"
```

Expected: `OK clean`.

- [ ] **Step 4: Commit**

```bash
git add template/optional/obsidian/agents
git commit -m "feat: vendor verifier, wiki-ingest, wiki-lint agents"
```

---

## Task 4: Vendor the 3 commands

**Files:**
- Create: `template/optional/obsidian/commands/{wiki,save,canvas}.md`

- [ ] **Step 1: Copy verbatim**

```bash
cd /home/omer/Projects/team_ai
for c in wiki save canvas; do
  cp /home/omer/Projects/claude-obsidian-ref/commands/$c.md template/optional/obsidian/commands/$c.md
done
```

- [ ] **Step 2: Trim dropped-feature references**

Open `commands/canvas.md` and remove any `/autoresearch` mention. Open
`commands/wiki.md` and `commands/save.md` and remove references to `wiki-cli`,
`wiki-mode`, or `/autoresearch` if present.

- [ ] **Step 3: Verify clean**

```bash
cd /home/omer/Projects/team_ai
grep -rniE 'wiki-cli|wiki-mode|wiki-fold|autoresearch|dragonscale' template/optional/obsidian/commands \
  && echo "FAIL" || echo "OK clean"
```

Expected: `OK clean`.

- [ ] **Step 4: Commit**

```bash
git add template/optional/obsidian/commands
git commit -m "feat: vendor /wiki, /save, /canvas commands"
```

---

## Task 5: Vendor the 3 kept scripts

**Files:**
- Create: `template/optional/obsidian/scripts/{detect-transport.sh,wiki-lock.sh,setup-vault.sh}`

- [ ] **Step 1: Copy the three kept scripts**

```bash
cd /home/omer/Projects/team_ai
cp /home/omer/Projects/claude-obsidian-ref/scripts/detect-transport.sh template/optional/obsidian/scripts/
cp /home/omer/Projects/claude-obsidian-ref/scripts/wiki-lock.sh         template/optional/obsidian/scripts/
cp /home/omer/Projects/claude-obsidian-ref/bin/setup-vault.sh           template/optional/obsidian/scripts/
chmod +x template/optional/obsidian/scripts/*.sh
```

- [ ] **Step 2: Trim dropped-feature wiring inside the scripts**

Open each script and remove blocks that set up or call dropped features:
- `setup-vault.sh`: remove any steps that download Excalidraw `main.js`, set up
  DragonScale, retrieval, ollama, or methodology modes. Keep only: create the
  `wiki/` folder structure, `_templates/`, and `.vault-meta/`. Keep the script
  runnable without the Obsidian desktop app present (it should `mkdir -p` the
  structure and print a notice; any Obsidian-app-specific step must be guarded so
  the script still exits 0 without the app).
- `detect-transport.sh`: if it references `wiki-cli` setup or retrieval
  transports that we dropped, leave the *detection* (it gracefully falls back to
  filesystem) but ensure it never hard-fails when those transports are absent.
- `wiki-lock.sh`: vendored as-is (pure filesystem locking, no dropped deps).

- [ ] **Step 3: Smoke-test the scripts don't reference missing siblings**

```bash
cd /home/omer/Projects/team_ai
bash -n template/optional/obsidian/scripts/detect-transport.sh && echo "detect-transport OK"
bash -n template/optional/obsidian/scripts/wiki-lock.sh && echo "wiki-lock OK"
bash -n template/optional/obsidian/scripts/setup-vault.sh && echo "setup-vault OK"
grep -niE 'allocate-address|tiling-check|retrieve\.py|bm25|rerank|setup-retrieve|setup-dragonscale|setup-mode' \
  template/optional/obsidian/scripts/*.sh && echo "FAIL ref" || echo "OK clean"
```

Expected: three `OK` syntax lines and `OK clean`.

- [ ] **Step 4: Commit**

```bash
git add template/optional/obsidian/scripts
git commit -m "feat: vendor detect-transport, wiki-lock, setup-vault scripts"
```

---

## Task 6: Vendor the 5 note templates

**Files:**
- Create: `template/optional/obsidian/templates/{source,entity,concept,question,comparison}.md`

- [ ] **Step 1: Copy the five templates**

```bash
cd /home/omer/Projects/team_ai
for t in source entity concept question comparison; do
  cp /home/omer/Projects/claude-obsidian-ref/_templates/$t.md template/optional/obsidian/templates/$t.md
done
```

- [ ] **Step 2: Verify they are mode-neutral (no dropped-feature frontmatter)**

```bash
cd /home/omer/Projects/team_ai
grep -rniE 'dragonscale|wiki-mode|address-counter|tiling' template/optional/obsidian/templates \
  && echo "FAIL" || echo "OK clean"
ls template/optional/obsidian/templates | sort
```

Expected: `OK clean` and the five `.md` files listed.

- [ ] **Step 3: Commit**

```bash
git add template/optional/obsidian/templates
git commit -m "feat: vendor 5 Obsidian note templates"
```

---

## Task 7: Author the minimal wiki seed

**Files:**
- Create: `template/optional/obsidian/wiki-seed/{index.md,hot.md,log.md,overview.md}`
- Create: `template/optional/obsidian/wiki-seed/{concepts,entities,sources,questions,comparisons}/.gitkeep`

Authored fresh (the ref `wiki/` is bloated demo content — we want a clean skeleton).

- [ ] **Step 1: Create the folder skeleton with .gitkeep**

```bash
cd /home/omer/Projects/team_ai
for d in concepts entities sources questions comparisons; do
  mkdir -p template/optional/obsidian/wiki-seed/$d
  : > template/optional/obsidian/wiki-seed/$d/.gitkeep
done
```

- [ ] **Step 2: Write `wiki-seed/index.md`**

```markdown
---
type: meta
title: Wiki Index
status: evergreen
tags: [meta, index]
---

# Wiki Index

Navigation: [[overview]] | [[log]] | [[hot]]

The master catalog of this vault. New pages are filed under one of:
`concepts/`, `entities/`, `sources/`, `questions/`, `comparisons/`.

## Concepts

_(none yet)_

## Entities

_(none yet)_

## Sources

_(none yet)_

## Questions

_(none yet)_

## Comparisons

_(none yet)_
```

- [ ] **Step 3: Write `wiki-seed/hot.md`**

```markdown
---
type: meta
title: Hot Cache
status: evergreen
tags: [meta, hot]
---

# Hot Cache

This is a cache, not a journal. It holds the most recent working context so a
new session can resume quickly. Overwrite it completely when it changes; keep it
under 500 words.

## Last Updated

_(never — fresh vault)_

## Key Recent Facts

_(none yet)_

## Recent Changes

_(none yet)_

## Active Threads

_(none yet)_
```

- [ ] **Step 4: Write `wiki-seed/log.md`**

```markdown
---
type: meta
title: Operation Log
status: evergreen
tags: [meta, log]
---

# Operation Log

Append-only. New entries go at the **top**. Format:
`## [YYYY-MM-DD] <operation> | <title>`

<!-- entries below -->
```

- [ ] **Step 5: Write `wiki-seed/overview.md`**

```markdown
---
type: overview
title: Wiki Overview
status: developing
tags: [meta, overview]
---

# Wiki Overview

This vault is the team's shared, durable knowledge memory. It follows the
LLM Wiki Pattern: sources are ingested into summary pages, and the durable
ideas/entities they contain are cross-linked under `concepts/` and `entities/`.

Agents query this vault for prior context before re-reading raw material, and
save sprint closeouts here as lasting memory.

## How to use it

- `/wiki` — route a knowledge operation (ingest, query, lint).
- `/save` — persist a note or closeout into the vault.
- `/canvas` — build a visual board of linked pages.
```

- [ ] **Step 6: Commit**

```bash
git add template/optional/obsidian/wiki-seed
git commit -m "feat: author minimal wiki/ seed skeleton"
```

---

## Task 8: Author hooks.json (3 kept hooks) + permissions.json

**Files:**
- Create: `template/optional/obsidian/hooks/hooks.json`
- Create: `template/optional/obsidian/permissions.json`

- [ ] **Step 1: Write `hooks/hooks.json`** (SessionStart + PostCompact + Stop only; `scripts/` rewritten to `.claude/scripts/`; PostToolUse dropped)

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "[ -f wiki/hot.md ] && cat wiki/hot.md || true"
          },
          {
            "type": "command",
            "command": "[ -x .claude/scripts/wiki-lock.sh ] && bash .claude/scripts/wiki-lock.sh clear-stale --max-age 3600 >/dev/null 2>&1 || true"
          },
          {
            "type": "prompt",
            "prompt": "If a vault is configured for this session (a wiki/ folder exists in the current directory), silently read wiki/hot.md to restore recent context. If wiki/hot.md does not exist, do nothing. Do not announce this. Do not report what you read. Just have the context available."
          }
        ]
      }
    ],
    "PostCompact": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Hook-injected context does not survive context compaction. If wiki/hot.md exists in the current directory, silently re-read it now to restore the hot cache. Do not announce this."
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"$PWD\" && [ -d wiki ] && [ -d .git ] && git diff --name-only HEAD 2>/dev/null | grep -q '^wiki/' && echo 'WIKI_CHANGED: Wiki pages were modified this session. Please update wiki/hot.md with a brief summary of what changed (under 500 words). Use the hot cache format: Last Updated, Key Recent Facts, Recent Changes, Active Threads. Keep it factual. Overwrite the file completely. It is a cache, not a journal.' || true"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Write `permissions.json`** (extra `settings.json` allow entries the scripts/hooks need)

```json
{
  "allow": [
    "Bash(bash .claude/scripts/wiki-lock.sh:*)",
    "Bash(bash .claude/scripts/detect-transport.sh:*)",
    "Bash(bash .claude/scripts/setup-vault.sh:*)",
    "Bash(.claude/scripts/wiki-lock.sh:*)",
    "Bash(.claude/scripts/detect-transport.sh:*)",
    "Bash(.claude/scripts/setup-vault.sh:*)",
    "Bash(mkdir:*)"
  ]
}
```

- [ ] **Step 3: Validate both are valid JSON and PostToolUse is absent**

```bash
cd /home/omer/Projects/team_ai
python3 -c "import json; h=json.load(open('template/optional/obsidian/hooks/hooks.json')); assert set(h['hooks'])=={'SessionStart','PostCompact','Stop'}, h['hooks'].keys(); print('hooks OK')"
python3 -c "import json; p=json.load(open('template/optional/obsidian/permissions.json')); assert 'allow' in p and isinstance(p['allow'], list); print('perms OK')"
```

Expected: `hooks OK` and `perms OK`.

- [ ] **Step 4: Commit**

```bash
git add template/optional/obsidian/hooks template/optional/obsidian/permissions.json
git commit -m "feat: author kept hooks (no auto-commit) and extra permissions"
```

---

## Task 9: Author the 5 awareness snippets

**Files:**
- Create: `template/optional/obsidian/snippets/{claude-section,researcher,reviewer,planner-implementer,team}.md`

Each snippet's content is wrapped in module markers so scaffold-time substitution
and in-place injection produce identical blocks. **Important:** snippet bodies
must not contain a literal `$` followed by a name unless escaped as `$$` — they
are passed through `string.Template`. Use plain prose; the slash-command tokens
below contain no `$`.

- [ ] **Step 1: Write `snippets/claude-section.md`**

```markdown

<!-- obsidian:module:start -->
## Knowledge Vault

This project has an Obsidian-backed **knowledge vault** at `wiki/` — the team's
shared, durable memory. Prefer querying the vault for prior context over
re-reading raw `resource/` files.

- `/wiki` — route a knowledge operation (ingest a source, query, lint).
- `/save` — persist a note or a sprint closeout into the vault.
- `/canvas` — build a visual board of linked pages.

Vault pages under `wiki/` are tracked and committed through the normal sprint
flow: `@<nickname>:` commit subjects on the `sprint/<slug>` branch (see the
`using-git` skill). Runtime artifacts under `.vault-meta/` are git-ignored.
Multi-writer safety is handled by `.claude/scripts/wiki-lock.sh`.
<!-- obsidian:module:end -->
```

- [ ] **Step 2: Write `snippets/researcher.md`**

```markdown

<!-- obsidian:module:start -->
## Knowledge Vault (Researcher)

This project has an Obsidian knowledge vault at `wiki/`. Before re-reading raw
sources, **query the vault** for what the team already knows. When you bring in a
new source, **ingest it** rather than just summarizing it inline:

- Ingest sources with `/wiki` (the `wiki-ingest` skill / agent) so they become
  durable, cross-linked pages under `wiki/sources/` and `wiki/concepts/`.
- Query with `/wiki` (the `wiki-query` skill) to retrieve prior findings.

Your synthesized findings should link to the vault pages you created or used.
<!-- obsidian:module:end -->
```

- [ ] **Step 3: Write `snippets/reviewer.md`**

```markdown

<!-- obsidian:module:start -->
## Knowledge Vault (Reviewer)

When a sprint closes, **`/save` the Sprint Closeout into the knowledge vault** as
durable team memory: a short page under `wiki/` capturing what shipped, the
verdict, and any follow-ups. This makes the closeout queryable by future sprints
instead of being buried in `plan.md`.
<!-- obsidian:module:end -->
```

- [ ] **Step 4: Write `snippets/planner-implementer.md`**

```markdown

<!-- obsidian:module:start -->
**Knowledge vault:** before starting, check the `wiki/` vault (via `/wiki` query)
for relevant prior decisions, prior art, and closeouts from earlier sprints.
<!-- obsidian:module:end -->
```

- [ ] **Step 5: Write `snippets/team.md`**

```markdown

<!-- obsidian:module:start -->
## Shared Memory

This team has an Obsidian knowledge vault at `wiki/` — shared, durable memory.
Agents query it for prior context and save findings/closeouts into it.
<!-- obsidian:module:end -->
```

- [ ] **Step 6: Verify snippets are `string.Template`-safe**

```bash
cd /home/omer/Projects/team_ai
python3 - <<'PY'
from string import Template
import glob
for f in glob.glob("template/optional/obsidian/snippets/*.md"):
    Template(open(f).read()).substitute({})  # raises if any unescaped $var
    print("OK", f)
PY
```

Expected: one `OK` line per snippet, no exception.

- [ ] **Step 7: Commit**

```bash
git add template/optional/obsidian/snippets
git commit -m "feat: author 5 vault-awareness snippets"
```

---

## Task 10: Add `$obsidian_*` placeholders to the .tmpl files

**Files:**
- Modify: `template/CLAUDE.md.tmpl` (add `$obsidian_section`)
- Modify: `template/claude/agents/researcher.md.tmpl` (add `$obsidian_researcher`)
- Modify: `template/claude/agents/reviewer.md.tmpl` (add `$obsidian_reviewer`)
- Modify: `template/claude/agents/planner.md.tmpl` (add `$obsidian_note`)
- Modify: `template/claude/agents/implementer.md.tmpl` (add `$obsidian_note`)
- Modify: `template/claude/team.md.tmpl` (add `$obsidian_team`)

Because the variables render to `""` when disabled, placement just needs to be on
its own line so an empty value leaves no stray blank-line artifact that would
break the byte-identical-default guarantee. **Key:** the placeholder line must be
exactly `$obsidian_section` (etc.) with nothing else, so when it renders to `""`
the line becomes empty — and the surrounding text already has blank lines, so a
single empty line is absorbed. Verify the disabled-default test (Task 11) passes;
if an extra blank line breaks a byte-comparison, adjust by placing the variable
immediately adjacent to existing text with no surrounding blank line.

- [ ] **Step 1: CLAUDE.md.tmpl — insert `$obsidian_section` before the `## 7. Git & Version Control` section**

Find the line `## 7. Git & Version Control` and insert immediately above it (so the vault section becomes a natural part of the doc):

```
$obsidian_section

## 7. Git & Version Control
```

- [ ] **Step 2: researcher.md.tmpl — insert `$obsidian_researcher` after the "## Your Role" paragraph**

After the `Your output is a synthesized findings document — not implementation code.` line, add a blank line then:

```
$obsidian_researcher
```

- [ ] **Step 3: reviewer.md.tmpl — insert `$obsidian_reviewer` after the "## Your Role" paragraph**

After `Your verdict is recorded in `plan.md` as the **Sprint Closeout**.` add a blank line then:

```
$obsidian_reviewer
```

- [ ] **Step 4: planner.md.tmpl — insert `$obsidian_note` near the top of the role section**

Open `template/claude/agents/planner.md.tmpl`, find the end of the first role
paragraph (the "## Your Role" section), and insert on its own line after it:

```
$obsidian_note
```

- [ ] **Step 5: implementer.md.tmpl — insert `$obsidian_note` near the top of the role section**

Open `template/claude/agents/implementer.md.tmpl`, find the end of the first role
paragraph, and insert on its own line after it:

```
$obsidian_note
```

- [ ] **Step 6: team.md.tmpl — insert `$obsidian_team` before the `## Conventions` section**

Find `## Conventions` in `template/claude/team.md.tmpl` and insert immediately above it:

```
$obsidian_team

## Conventions
```

- [ ] **Step 7: Verify the placeholders parse and reference only known names**

```bash
cd /home/omer/Projects/team_ai
grep -rn 'obsidian_' template/CLAUDE.md.tmpl template/claude/agents/researcher.md.tmpl \
  template/claude/agents/reviewer.md.tmpl template/claude/agents/planner.md.tmpl \
  template/claude/agents/implementer.md.tmpl template/claude/team.md.tmpl
```

Expected: exactly one `$obsidian_section`, one `$obsidian_researcher`, one
`$obsidian_reviewer`, one `$obsidian_note` in planner, one `$obsidian_note` in
implementer, one `$obsidian_team`.

- [ ] **Step 8: Commit**

```bash
git add template/CLAUDE.md.tmpl template/claude/agents/researcher.md.tmpl \
  template/claude/agents/reviewer.md.tmpl template/claude/agents/planner.md.tmpl \
  template/claude/agents/implementer.md.tmpl template/claude/team.md.tmpl
git commit -m "feat: add \$obsidian_* placeholders to team templates"
```

---

## Task 11: Wire obsidian-var helper into all render mappings (disabled path)

**Files:**
- Modify: `setup.py` (add `OBSIDIAN_SNIPPET_VARS`, `_obsidian_vars()`, spread into every render mapping; add `OPTIONAL_DIR`)
- Test: `tests/test_obsidian_module.py`

This task makes the **disabled** path correct: every template var resolves (to
`""`) so `render_template` never raises, and no `$obsidian_*` leaks into output.

- [ ] **Step 1: Write the failing test (disabled default has no leftover placeholders)**

Create `tests/test_obsidian_module.py`:

```python
import unittest
import tempfile
import shutil
import sys
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
        # No rendered file may contain a leftover $obsidian_ placeholder.
        for path in self.target.rglob("*"):
            if path.is_file() and path.suffix in (".md", ".json"):
                text = path.read_text(errors="ignore")
                self.assertNotIn("$obsidian_", text, f"leftover placeholder in {path}")

    def test_disabled_creates_no_obsidian_artifacts(self):
        scaffold_project(self.target, minimal=True, force=False)
        self.assertFalse((self.target / "wiki").exists(), "wiki/ must not exist when disabled")
        self.assertFalse((self.target / ".claude" / "skills" / "wiki").exists())
        self.assertFalse((self.target / ".claude" / "commands" / "wiki.md").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it — expect failure (render raises on unknown `$obsidian_*`)**

Run: `cd /home/omer/Projects/team_ai && python -m pytest tests/test_obsidian_module.py -v`
Expected: FAIL — `RenderError: template references undefined variable: '...obsidian_section...'` (because Task 10 added placeholders but setup.py doesn't supply them yet).

- [ ] **Step 3: Add the obsidian-var helper to setup.py**

After `TEMPLATE_DIR = REPO_ROOT / "template"` (line ~113), add:

```python
OPTIONAL_DIR = TEMPLATE_DIR / "optional"
OBSIDIAN_DIR = OPTIONAL_DIR / "obsidian"

# Maps each $obsidian_* template variable to its snippet file under
# template/optional/obsidian/snippets/. planner+implementer share one snippet.
OBSIDIAN_SNIPPET_VARS = {
    "obsidian_section": "claude-section.md",
    "obsidian_researcher": "researcher.md",
    "obsidian_reviewer": "reviewer.md",
    "obsidian_note": "planner-implementer.md",
    "obsidian_team": "team.md",
}


def _obsidian_vars(enabled: bool) -> dict:
    """Return the $obsidian_* render mapping.

    When enabled, each var holds its snippet's content; when disabled, "".
    Every render_template call spreads this in so templates always resolve.
    """
    if not enabled:
        return {k: "" for k in OBSIDIAN_SNIPPET_VARS}
    snippets_dir = OBSIDIAN_DIR / "snippets"
    return {
        var: (snippets_dir / fname).read_text()
        for var, fname in OBSIDIAN_SNIPPET_VARS.items()
    }
```

- [ ] **Step 4: Thread an `obsidian` flag through `scaffold_project` and spread vars into every render mapping**

Change the `scaffold_project` signature to accept the flag and compute the vars once:

```python
def scaffold_project(target: Path, minimal: bool = False, force: bool = False,
                     obsidian: bool = False) -> int:
```

Immediately after the `minimal` / wizard branch resolves `project_name,
description, roster`, add:

```python
    obsidian_vars = _obsidian_vars(obsidian)
```

Then update each `render_template(...)` call to spread it in. CLAUDE.md:

```python
    (target / "CLAUDE.md").write_text(
        render_template(claude_tmpl, {
            "project_name": project_name,
            "description": description or "(no description provided)",
            **obsidian_vars,
        })
    )
```

team.md:

```python
    (target / ".claude" / "team.md").write_text(
        render_template(team_tmpl, {
            "project_name": project_name,
            "roster_block": _render_roster_block(roster),
            **obsidian_vars,
        })
    )
```

Each agent render in the install loop:

```python
        rendered = render_template(tmpl_path.read_text(), {
            "nickname": nickname,
            "project_name": project_name,
            **obsidian_vars,
        })
```

(Spreading all five keys into every mapping is intentional — `string.Template`
ignores keys a given template does not reference.)

- [ ] **Step 5: Update `_write_team_md` and `add_agent` to supply obsidian vars too**

`_write_team_md` and `add_agent`'s render call run during in-place ops on
projects that may or may not have the module. To keep them from raising on the
new placeholders, supply disabled-by-default vars there. In `_write_team_md`:

```python
def _write_team_md(project: Path, project_name: str, roster: dict,
                   obsidian_vars: dict | None = None) -> None:
    team_tmpl = (TEMPLATE_DIR / "claude" / "team.md.tmpl").read_text()
    (project / ".claude" / "team.md").write_text(
        render_template(team_tmpl, {
            "project_name": project_name,
            "roster_block": _render_roster_block(roster),
            **(obsidian_vars or _obsidian_vars(False)),
        })
    )
```

In `add_agent`, update its `render_template` call to spread `**_obsidian_vars(False)`.

> Note: when these in-place ops run inside a *generated* project, `TEMPLATE_DIR`
> resolves relative to the bundled `team_setup.py` copy. Task 12 ensures the
> `optional/obsidian/snippets/` are bundled so `_obsidian_vars(True)` works
> there too; for the disabled default `_obsidian_vars(False)` reads no files.

- [ ] **Step 6: Run the test — expect pass**

Run: `cd /home/omer/Projects/team_ai && python -m pytest tests/test_obsidian_module.py -v`
Expected: both `TestObsidianDisabledDefault` tests PASS.

- [ ] **Step 7: Run the full suite — all existing tests still pass**

Run: `cd /home/omer/Projects/team_ai && python -m pytest -q`
Expected: all existing tests (12+) and the 2 new tests PASS.

- [ ] **Step 8: Commit**

```bash
git add setup.py tests/test_obsidian_module.py
git commit -m "feat: supply \$obsidian_* vars in render mappings (disabled path)"
```

---

## Task 12: `apply_obsidian_module` merge + `--with-obsidian` flag + wizard + settings merge

**Files:**
- Modify: `setup.py` (`apply_obsidian_module`, `_merge_settings_json`, CLI flag, wizard, scaffold call-through, bundle `optional/` for in-place, print notice)
- Modify: `tests/test_obsidian_module.py` (enabled-scaffold assertions)

- [ ] **Step 1: Write the failing enabled-scaffold test**

Append to `tests/test_obsidian_module.py`:

```python
import json


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
        # original permissions preserved
        self.assertIn("Read", allow)
        hooks = settings["hooks"]
        self.assertEqual(set(hooks), {"SessionStart", "PostCompact", "Stop"})
        self.assertNotIn("PostToolUse", hooks)
        # no auto-commit command anywhere
        self.assertNotIn("auto-commit", json.dumps(hooks))

    def test_gitignore_has_vault_meta(self):
        gi = (self.target / ".gitignore").read_text()
        self.assertIn(".vault-meta/", gi)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it — expect failure**

Run: `cd /home/omer/Projects/team_ai && python -m pytest tests/test_obsidian_module.py::TestObsidianEnabled -v`
Expected: FAIL — the module isn't copied yet (no `apply_obsidian_module`).

- [ ] **Step 3: Implement `_merge_settings_json` in setup.py**

Add near the other helpers:

```python
import json


def _merge_settings_json(settings_path: Path) -> None:
    """Merge obsidian permissions + hooks into an existing settings.json.

    Dedupes permission entries against what's already present and adds the
    three kept hooks. Idempotent.
    """
    settings = json.loads(settings_path.read_text())

    extra = json.loads((OBSIDIAN_DIR / "permissions.json").read_text())
    allow = settings.setdefault("permissions", {}).setdefault("allow", [])
    for entry in extra.get("allow", []):
        if entry not in allow:
            allow.append(entry)

    hooks_def = json.loads((OBSIDIAN_DIR / "hooks" / "hooks.json").read_text())
    settings["hooks"] = hooks_def["hooks"]  # kept hooks only; replaces any prior

    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
```

- [ ] **Step 4: Implement `apply_obsidian_module` in setup.py**

```python
def apply_obsidian_module(target: Path) -> None:
    """Merge the Obsidian module into a target .claude/ + project root.

    1. Merge skills/ agents/ commands/ scripts/ templates/ into .claude/.
    2. Drop wiki-seed/ as wiki/ at the project root.
    3. Merge permissions + hooks into .claude/settings.json.
    4. Add .vault-meta/ to the project .gitignore.

    Idempotent: re-running overwrites module files and re-dedupes settings.
    """
    claude = target / ".claude"

    # 1. Merge per-item trees into .claude/ (preserve existing siblings).
    for sub in ("skills", "agents", "commands", "scripts", "templates"):
        src = OBSIDIAN_DIR / sub
        dst = claude / sub
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            target_item = dst / item.name
            if item.is_dir():
                if target_item.exists():
                    shutil.rmtree(target_item)
                shutil.copytree(item, target_item)
            else:
                shutil.copy(item, target_item)
        # keep scripts executable
        if sub == "scripts":
            for sh in dst.glob("*.sh"):
                sh.chmod(0o755)

    # 2. Drop the wiki seed at the project root.
    wiki_dst = target / "wiki"
    src_seed = OBSIDIAN_DIR / "wiki-seed"
    for item in src_seed.rglob("*"):
        rel = item.relative_to(src_seed)
        out = wiki_dst / rel
        if item.is_dir():
            out.mkdir(parents=True, exist_ok=True)
        elif item.name == ".gitkeep":
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("")
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(item, out)

    # 3. Merge settings.json.
    _merge_settings_json(claude / "settings.json")

    # 4. Add .vault-meta/ to the project .gitignore.
    gitignore = target / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else ""
    if ".vault-meta/" not in existing:
        prefix = "" if existing.endswith("\n") or not existing else "\n"
        addition = "\n# Obsidian vault runtime artifacts\n.vault-meta/\n"
        gitignore.write_text(existing + prefix + addition)
```

- [ ] **Step 5: Call `apply_obsidian_module` at the end of `scaffold_project` (when enabled) and bundle `optional/` for in-place ops**

Just before the final `print(...)` block in `scaffold_project`, add:

```python
    if obsidian:
        apply_obsidian_module(target)
```

The in-place bundle copy currently does:

```python
    shutil.copytree(
        TEMPLATE_DIR, template_dst,
        ignore=shutil.ignore_patterns("skills", "scripts"),
    )
```

`optional/` is under `TEMPLATE_DIR`, so it is already bundled — but the
`ignore_patterns("skills", "scripts")` would also strip
`optional/obsidian/skills` and `.../scripts`, breaking in-place `--add-obsidian`.
Change the ignore to only strip the **top-level** always-copied skills/scripts,
not the optional ones, by using a path-aware ignore:

```python
    def _bundle_ignore(dir_path, names):
        # Strip only template/claude/skills and template/claude/scripts;
        # keep everything under template/optional/.
        dp = Path(dir_path)
        if dp.name == "claude" and dp.parent == TEMPLATE_DIR:
            return {n for n in names if n in ("skills", "scripts")}
        return set()

    shutil.copytree(TEMPLATE_DIR, template_dst, ignore=_bundle_ignore)
```

- [ ] **Step 6: Update the success notice when the module is added**

Replace the final scaffold print block to mention the module when enabled:

```python
    print(f"✓ Project scaffolded at {target}")
    print("  Next: drop knowledge into resource/, then run /sprint-start \"<goal>\"")
    if obsidian:
        print("  Obsidian module added — run "
              "`.claude/scripts/setup-vault.sh` to wire up the Obsidian app.")
    return 0
```

- [ ] **Step 7: Add the `--with-obsidian` CLI flag and wizard question**

In `_build_parser`, add:

```python
    p.add_argument("--with-obsidian", action="store_true",
                   help="Include the opt-in Obsidian knowledge-vault module")
```

In `main`, pass it through to scaffold:

```python
    return scaffold_project(target, minimal=args.minimal, force=args.force,
                            obsidian=args.with_obsidian)
```

In `run_wizard`, after the description prompt (before specialist selection),
ask the question and return it; change the return signature to include it:

```python
    obsidian = _ask_yes_no(
        "Include the Obsidian knowledge-vault module?", default_no=True)
    ...
    return project_name, description, roster, obsidian
```

Update the wizard caller in `scaffold_project`:

```python
    if minimal:
        project_name = target.name
        description = ""
        roster = {role: AGENTS[role][1] for role in MINIMAL_AGENTS}
        # obsidian stays as the passed-in flag value
    else:
        project_name, description, roster, wiz_obsidian = run_wizard(target)
        obsidian = obsidian or wiz_obsidian
```

(`--with-obsidian` forces it on even in wizard mode; the wizard can also enable it.)

- [ ] **Step 8: Run the enabled test — expect pass**

Run: `cd /home/omer/Projects/team_ai && python -m pytest tests/test_obsidian_module.py -v`
Expected: all `TestObsidianEnabled` + `TestObsidianDisabledDefault` tests PASS.

- [ ] **Step 9: Run the full suite**

Run: `cd /home/omer/Projects/team_ai && python -m pytest -q`
Expected: all tests PASS (existing default-tree tests confirm disabled output unchanged).

- [ ] **Step 10: Commit**

```bash
git add setup.py tests/test_obsidian_module.py
git commit -m "feat: --with-obsidian scaffold, module merge, settings + hooks merge"
```

---

## Task 13: In-place `--add-obsidian` op (idempotent injection)

**Files:**
- Modify: `setup.py` (`add_obsidian` in-place op, CLI flag, marker-injection helper)
- Modify: `tests/test_obsidian_module.py` (in-place assertions)

- [ ] **Step 1: Write the failing in-place test**

Append to `tests/test_obsidian_module.py`:

```python
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
        # Same artifacts as a --with-obsidian scaffold.
        self.assertTrue((c / "skills" / "wiki" / "SKILL.md").is_file())
        self.assertTrue((c / "commands" / "wiki.md").is_file())
        self.assertTrue((c / "agents" / "verifier.md").is_file())
        self.assertTrue((self.target / "wiki" / "hot.md").is_file())
        settings = json.loads((c / "settings.json").read_text())
        self.assertEqual(set(settings["hooks"]),
                         {"SessionStart", "PostCompact", "Stop"})
        # Awareness block injected into the already-rendered CLAUDE.md.
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
        # No duplicate injection, no duplicate permission entries.
        self.assertEqual(claude_once.count("obsidian:module:start"),
                         claude_twice.count("obsidian:module:start"))
        self.assertEqual(claude_once, claude_twice)
        self.assertEqual(settings_once, settings_twice)
```

- [ ] **Step 2: Run it — expect failure**

Run: `cd /home/omer/Projects/team_ai && python -m pytest tests/test_obsidian_module.py::TestObsidianInPlace -v`
Expected: FAIL — `ImportError: cannot import name 'add_obsidian'`.

- [ ] **Step 3: Implement the marker-injection helper and `add_obsidian`**

Add to setup.py:

```python
OBSIDIAN_MARKER_START = "<!-- obsidian:module:start -->"


def _inject_snippet(file_path: Path, snippet_file: str) -> None:
    """Append a marker-wrapped snippet to file_path if not already present.

    Idempotent: a file already containing the start marker is left untouched.
    """
    if not file_path.is_file():
        return
    text = file_path.read_text()
    if OBSIDIAN_MARKER_START in text:
        return
    snippet = (OBSIDIAN_DIR / "snippets" / snippet_file).read_text()
    sep = "" if text.endswith("\n") else "\n"
    file_path.write_text(text + sep + snippet.rstrip("\n") + "\n")


def add_obsidian(project: Path) -> int:
    """In-place: add the Obsidian module to an already-scaffolded project."""
    _require_project(project)
    apply_obsidian_module(project)

    # Inject awareness blocks into the already-rendered files.
    _inject_snippet(project / "CLAUDE.md", "claude-section.md")
    _inject_snippet(project / ".claude" / "team.md", "team.md")
    roster = _read_team_roster(project)
    agent_snippets = {
        "researcher": "researcher.md",
        "reviewer": "reviewer.md",
        "planner": "planner-implementer.md",
        "implementer": "planner-implementer.md",
    }
    for role, snippet in agent_snippets.items():
        if role in roster:
            _inject_snippet(project / ".claude" / "agents" / f"{role}.md", snippet)

    print("✓ Obsidian module added to the project")
    print("  Run `.claude/scripts/setup-vault.sh` to wire up the Obsidian app.")
    return 0
```

- [ ] **Step 4: Wire the `--add-obsidian` CLI flag**

In `_build_parser`, add alongside the other in-place ops:

```python
    p.add_argument("--add-obsidian", action="store_true",
                   help="Add the Obsidian module to an existing project (in-place)")
```

In `main`, include it in the in-place dispatch:

```python
    in_place_flags = (args.list_team, args.rename, args.add_agent,
                      args.remove_agent, args.add_obsidian)
    if any(in_place_flags):
        project = Path(args.target).resolve() if args.target else Path.cwd()
        if args.list_team:
            return list_team(project)
        if args.rename:
            return rename_agent(project, args.rename)
        if args.add_agent:
            return add_agent(project, args.add_agent)
        if args.remove_agent:
            return remove_agent(project, args.remove_agent)
        if args.add_obsidian:
            return add_obsidian(project)
```

- [ ] **Step 5: Run the in-place test — expect pass**

Run: `cd /home/omer/Projects/team_ai && python -m pytest tests/test_obsidian_module.py::TestObsidianInPlace -v`
Expected: both in-place tests PASS.

- [ ] **Step 6: Run the full suite**

Run: `cd /home/omer/Projects/team_ai && python -m pytest -q`
Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add setup.py tests/test_obsidian_module.py
git commit -m "feat: --add-obsidian in-place op with idempotent injection"
```

---

## Task 14: End-to-end sanity + default-tree byte-identity guard

**Files:**
- Test: ad-hoc verification (no new file; relies on existing `test_scaffold.py` + new module tests)

- [ ] **Step 1: Confirm a real `--with-obsidian` scaffold works from the CLI**

```bash
cd /home/omer/Projects/team_ai
rm -rf /tmp/obs-demo && python setup.py /tmp/obs-demo --minimal --with-obsidian
ls /tmp/obs-demo/wiki /tmp/obs-demo/.claude/skills | head
python3 -c "import json,sys; s=json.load(open('/tmp/obs-demo/.claude/settings.json')); print('hooks:', list(s['hooks'])); assert 'PostToolUse' not in s['hooks']"
grep -c 'Knowledge Vault' /tmp/obs-demo/CLAUDE.md
```

Expected: wiki/ + skills listed; `hooks: ['SessionStart', 'PostCompact', 'Stop']`; `Knowledge Vault` count ≥ 1.

- [ ] **Step 2: Confirm a default scaffold is unchanged (no obsidian artifacts, no placeholders)**

```bash
cd /home/omer/Projects/team_ai
rm -rf /tmp/plain-demo && python setup.py /tmp/plain-demo --minimal
test ! -e /tmp/plain-demo/wiki && echo "no wiki OK"
grep -rl '\$obsidian_' /tmp/plain-demo && echo "FAIL placeholder leak" || echo "no placeholder leak OK"
```

Expected: `no wiki OK` and `no placeholder leak OK`.

- [ ] **Step 3: Confirm in-place add on the plain demo matches**

```bash
cd /home/omer/Projects/team_ai
python setup.py --add-obsidian /tmp/plain-demo
python setup.py --add-obsidian /tmp/plain-demo  # idempotent re-run
test -e /tmp/plain-demo/wiki/hot.md && echo "wiki seeded OK"
grep -c 'obsidian:module:start' /tmp/plain-demo/CLAUDE.md  # must be exactly 1
```

Expected: `wiki seeded OK` and a count of `1`.

- [ ] **Step 4: Run the entire suite one more time**

Run: `cd /home/omer/Projects/team_ai && python -m pytest -q`
Expected: all tests PASS.

- [ ] **Step 5: Clean up demo dirs (no commit — verification only)**

```bash
rm -rf /tmp/obs-demo /tmp/plain-demo
```

---

## Task 15: Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read the current README to find the right section**

Run: `sed -n '1,80p' /home/omer/Projects/team_ai/README.md` and locate where CLI
flags / scaffold usage are documented.

- [ ] **Step 2: Add an "Obsidian knowledge-vault module" section**

Add a section documenting:
- `python setup.py <target> --with-obsidian` — scaffold with the module.
- The wizard's yes/no question (default no).
- `python setup.py --add-obsidian [<project>]` — add it in-place to an existing
  project (idempotent).
- What the module adds: skills (`/wiki`, `/save`, `/canvas`), the `verifier` /
  `wiki-ingest` / `wiki-lint` agents, the `wiki/` vault seed, the three kept
  hooks (load/reload `hot.md`, lock hygiene — **no** auto-commit), extra
  `settings.json` permissions, and `.vault-meta/` added to `.gitignore`.
- The optional `.claude/scripts/setup-vault.sh` step for users who have the
  Obsidian desktop app.
- A note that the vault is committed through the normal sprint-branch +
  `@<nickname>:` flow, and that it's MIT-vendored from `claude-obsidian`
  (see `template/optional/obsidian/ATTRIBUTION.md`).

- [ ] **Step 3: Verify the README mentions the key tokens**

```bash
cd /home/omer/Projects/team_ai
grep -E -- '--with-obsidian|--add-obsidian|setup-vault.sh' README.md && echo "README OK"
```

Expected: matching lines and `README OK`.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document the Obsidian knowledge-vault module"
```

---

## Self-review checklist (run after implementation)

- [ ] **Spec coverage:** opt-in flag ✔ (T12) · wizard question ✔ (T12) · in-place add ✔ (T13) · curated 10 skills/3 agents/3 commands ✔ (T2–T4) · kept hooks only, no auto-commit ✔ (T8/T12) · wiki seed ✔ (T7) · scripts detect-transport+wiki-lock+setup-vault ✔ (T5) · templates ✔ (T6) · awareness wiring on CLAUDE/researcher/reviewer/planner/implementer/team ✔ (T9/T10) · settings permission merge w/ dedupe ✔ (T12) · `.vault-meta/` gitignored ✔ (T12) · default tree byte-identical ✔ (T11/T14, existing tests) · MIT attribution ✔ (T1) · README ✔ (T15).
- [ ] **No dropped feature leaks:** grep guards in T2/T3/T4/T5 enforce this.
- [ ] **No script-path dangling refs:** rewritten to `.claude/scripts/`, guarded in T2.
- [ ] **Type/name consistency:** `_obsidian_vars`, `OBSIDIAN_SNIPPET_VARS` keys (`obsidian_section/researcher/reviewer/note/team`), `apply_obsidian_module`, `add_obsidian`, `_merge_settings_json`, `_inject_snippet`, `OBSIDIAN_DIR` — used consistently T11→T13.
- [ ] **Existing tests pass:** verified at the end of T11, T12, T13, T14.

## Risks / watch-items during execution

- **Byte-identical default (the primary guard):** the `$obsidian_*` placeholders
  in Task 10 render to `""`. If a placeholder on its own line leaves a stray blank
  line that perturbs an existing test's expectation, adjust placement (Task 10
  step note). Run `test_scaffold.py` after Task 10/11.
- **`shutil.copytree` ignore for the in-place bundle (T12 step 5):** the original
  `ignore_patterns("skills","scripts")` would strip `optional/obsidian/skills` too.
  The path-aware `_bundle_ignore` fixes this — verify `--add-obsidian` works from a
  generated project's bundled `team_setup.py`, not just from the repo.
- **`json.dumps` reformatting `settings.json`:** the enabled path rewrites
  settings.json via `json.dumps(indent=2)`. That's fine (enabled projects differ),
  but ensure the **disabled** path never calls `_merge_settings_json`, so the plain
  `settings.json` stays the verbatim copied file.
- **Snippets through `string.Template`:** any literal `$` in a snippet must be
  `$$`. Guarded by Task 9 step 6.
```
