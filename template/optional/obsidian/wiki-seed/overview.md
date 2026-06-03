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
