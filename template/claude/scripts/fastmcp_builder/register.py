"""Project-scope Claude Code registration helper (T5).

This module deep-merges a FastMCP server entry into the project root
``.mcp.json`` file. It deliberately does NOT shell out to ``claude mcp add``
or ``fastmcp install claude-code`` — the architect chose committed-file
project-scope registration for reproducibility (see design.md §5).

Public API: :func:`register_project_scope`.
"""
from __future__ import annotations

import json
import os
import re
import warnings
from pathlib import Path
from typing import Any

from .errors import (
    InvalidSlug,
    MalformedConfig,
    OutsideProjectRoot,
    SecretLiteralRefused,
    ServerAlreadyRegistered,
)

__all__ = ["register_project_scope"]


# --- Regex constants ---------------------------------------------------------

_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
_SECRET_KEY_RE = re.compile(
    r"(?i)(secret|token|key|password|pass|api_key|auth)"
)
_PLACEHOLDER_RE = re.compile(r"^\$\{[A-Z_][A-Z0-9_]*\}$")
_FASTMCP_BUILDER_MARKER = "# fastmcp_builder"


# --- Public API --------------------------------------------------------------

def register_project_scope(
    server_name: str,
    server_path: Path,
    project_root: Path,
    env: dict[str, str] | None = None,
    deps: list[str] | None = None,
    overwrite: bool = False,
) -> dict:
    """Deep-merge a project-scope entry into ``<project_root>/.mcp.json``.

    Returns the entry dict that was written under ``mcpServers[server_name]``.
    Raises :class:`ServerAlreadyRegistered` if the slug exists and not
    ``overwrite``. Raises :class:`MalformedConfig` if the existing
    ``.mcp.json`` is not valid JSON.
    """
    if not _SLUG_RE.match(server_name):
        raise InvalidSlug(
            f"server_name {server_name!r} must match ^[a-z][a-z0-9-]{{0,39}}$"
        )

    env = env or {}
    deps = deps or []

    # Resolve relative path; this also enforces the OutsideProjectRoot guard.
    rel_path = _relative_posix(server_path, project_root)

    # Validate env values (may raise SecretLiteralRefused or warn).
    _validate_env(env)

    # Load or initialize the config (may raise MalformedConfig).
    cfg_path = project_root / ".mcp.json"
    cfg = _load_or_init_config(cfg_path)

    cfg.setdefault("mcpServers", {})
    if server_name in cfg["mcpServers"] and not overwrite:
        raise ServerAlreadyRegistered(
            f"server {server_name!r} already in {cfg_path}"
        )

    entry: dict[str, Any] = {
        "type": "stdio",
        "command": "uv",
        "args": _render_args(rel_path, deps),
        "env": dict(env),
    }
    cfg["mcpServers"][server_name] = entry

    _atomic_write(cfg_path, json.dumps(cfg, indent=2) + "\n")

    # Update .env.example with any ${VAR}-referenced keys.
    placeholder_keys = [k for k, v in env.items() if _PLACEHOLDER_RE.match(v)]
    if placeholder_keys:
        _merge_env_example(project_root / ".env.example", placeholder_keys)

    return entry


# --- Helpers -----------------------------------------------------------------

def _relative_posix(server_path: Path, project_root: Path) -> str:
    """Return server_path relative to project_root in POSIX form.

    Raises :class:`OutsideProjectRoot` if server_path is not under project_root.
    """
    try:
        rel = server_path.resolve().relative_to(project_root.resolve())
    except ValueError as exc:
        raise OutsideProjectRoot(
            f"{server_path} is not under project root {project_root}"
        ) from exc
    return rel.as_posix()


def _load_or_init_config(cfg_path: Path) -> dict:
    """Read+parse cfg_path or return {} if missing.

    Raises :class:`MalformedConfig` if the file exists but isn't valid JSON.
    """
    if not cfg_path.exists():
        return {}
    text = cfg_path.read_text(encoding="utf-8")
    try:
        cfg = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MalformedConfig(
            f"{cfg_path} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(cfg, dict):
        raise MalformedConfig(
            f"{cfg_path} top-level must be a JSON object, got {type(cfg).__name__}"
        )
    return cfg


def _validate_env(env: dict[str, str]) -> None:
    """Enforce the secret-handling policy from design.md §7 U3.

    - Secret-keyed literal => raise SecretLiteralRefused.
    - Secret-keyed placeholder => pass.
    - Non-secret literal => emit single grouped warning.
    """
    non_secret_literals: list[str] = []
    for k, v in env.items():
        is_placeholder = bool(_PLACEHOLDER_RE.match(v))
        is_secret_key = bool(_SECRET_KEY_RE.search(k))
        if is_secret_key and not is_placeholder:
            raise SecretLiteralRefused(
                f"env key {k!r} looks secret-y; pass a ${{VAR}} placeholder, "
                f"not the literal value (and add the real value to .env)."
            )
        if not is_secret_key and not is_placeholder:
            non_secret_literals.append(k)
    if non_secret_literals:
        warnings.warn(
            "Writing literal env values for non-secret keys: "
            f"{non_secret_literals}. Consider using ${{VAR}} placeholders.",
            UserWarning,
            stacklevel=3,
        )


def _render_args(rel_path: str, deps: list[str]) -> list[str]:
    """Build the ``args`` list per design.md §4."""
    args = ["run", "--with", "fastmcp"]
    for dep in deps:
        args.extend(["--with", dep])
    args.extend(["fastmcp", "run", rel_path])
    return args


def _atomic_write(path: Path, content: str) -> None:
    """Write content to path via tmp+os.replace in the same directory."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _merge_env_example(env_example_path: Path, new_keys: list[str]) -> None:
    """Merge new_keys into <project_root>/.env.example.

    - Preserves order of existing keys; never overwrites their values.
    - Appends new keys under a ``# fastmcp_builder`` comment if not present.
    - Atomic write.
    """
    existing_lines: list[str] = []
    existing_keys: set[str] = set()
    if env_example_path.exists():
        existing_lines = env_example_path.read_text(
            encoding="utf-8"
        ).splitlines()
        for line in existing_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key:
                    existing_keys.add(key)

    keys_to_add = [k for k in new_keys if k not in existing_keys]
    if not keys_to_add:
        # Nothing new to write; leave file untouched.
        return

    out_lines = list(existing_lines)
    has_marker = any(
        line.strip() == _FASTMCP_BUILDER_MARKER for line in out_lines
    )
    # Ensure separation if file is non-empty and last line is non-blank.
    if out_lines and out_lines[-1].strip() != "":
        out_lines.append("")
    if not has_marker:
        out_lines.append(_FASTMCP_BUILDER_MARKER)
    for k in keys_to_add:
        out_lines.append(f"{k}=")

    content = "\n".join(out_lines) + "\n"
    _atomic_write(env_example_path, content)
