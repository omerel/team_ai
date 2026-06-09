
<!-- obsidian:module:start -->
## Knowledge Vault (Researcher)

This project has an Obsidian knowledge vault at `wiki/`. Before re-reading raw
sources, **query the vault** for what the team already knows. When you bring in a
new source, **ingest it** rather than just summarizing it inline:

- Ingest sources with `/wiki` (the `wiki-ingest` skill / agent) so they become
  durable, cross-linked pages under `wiki/sources/` and `wiki/concepts/`.
- Query with `/wiki` (the `wiki-query` skill) to retrieve prior findings.
- For deep, autonomous research, invoke `/autoresearch [topic]` — it runs the loop independently and files everything into the vault.

Your synthesized findings should link to the vault pages you created or used.
<!-- obsidian:module:end -->
