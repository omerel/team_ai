# Attribution

The Obsidian knowledge-vault module vendored under `template/optional/obsidian/`
is a curated subset of the **claude-obsidian** project.

- **Upstream:** claude-obsidian by AgriciDaniel / AI Marketing Hub
- **License:** MIT (see `LICENSE` in this directory)
- **Underlying pattern:** the "LLM Wiki Pattern" (Andrej Karpathy)

## What was vendored

- Skills: `wiki`, `wiki-ingest`, `wiki-query`, `wiki-lint`, `save`, `canvas`,
  `defuddle`, `think`, `obsidian-markdown`, `obsidian-bases`, `autoresearch`
- Agents: `verifier`, `wiki-ingest`, `wiki-lint`
- Commands: `/wiki`, `/save`, `/canvas`
- Hooks: `SessionStart`, `PostCompact`, `Stop` (load/reload `hot.md` + lock hygiene)
- Scripts: `detect-transport.sh`, `wiki-lock.sh`, `setup-vault.sh`
- Note templates: `source`, `entity`, `concept`, `question`, `comparison`
- A minimal `wiki/` seed (authored for this module, not copied upstream)

## What was NOT vendored

- The retrieval pipeline (`wiki-retrieve`: BM25 / rerank / contextual-prefix)
- The `wiki-cli` transport layer, `wiki-mode` methodology modes
- `wiki-fold` / DragonScale
- The `PostToolUse` auto-commit hook (team-ai commits the vault through its
  normal sprint-branch + `@<nickname>:` flow instead)
- Benchmark/test harness, ollama integration, any API-egress paths

Script references and methodology hooks that pointed at the non-vendored
features were trimmed; script paths were rewritten to `.claude/scripts/`.
