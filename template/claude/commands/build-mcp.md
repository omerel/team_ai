---
description: Interactively build a FastMCP server scoped to the current project
---

Use the **fastmcp-builder** subagent to interactively build a FastMCP STDIO server in
the current project (the cwd from which this command is invoked).

Steps:
1. Read `.claude/team.md` to find the nickname assigned to the `fastmcp-builder`
   role, then dispatch that subagent. The agent will run the interview script
   defined in `.claude/agents/fastmcp-builder.md`.
2. Remind the agent of the project-root rule: it must write **only** under
   `<project_root>/mcp_code/**`, `<project_root>/.mcp.json`, and
   `<project_root>/.env.example`. No writes outside the project root, ever.
3. After files are written, the agent will print the resulting `.mcp.json` snippet
   for visual confirmation and (only if applicable) ask whether to run the
   subprocess smoke test. Do not run `claude mcp add`, `fastmcp install`, or
   `uv run` — the committed `.mcp.json` is the registration.

The agent is idempotent: re-invoking against an existing
`mcp_code/<slug>/spec.json` skips the early prompts and lets the guide adjust
tools.
