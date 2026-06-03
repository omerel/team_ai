
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
