"""FastMCP server generator (T4).

Pure-stdlib code generator for FastMCP servers. Renders ``mcp_code/<slug>/server.py``
and the ``mcp_code/<slug>/spec.json`` sidecar that is the source of truth for re-entry.

The template is implemented as Python f-strings; no Jinja2, no runtime deps.

Errors live in :mod:`fastmcp_builder.errors`. They are re-exported here so
callers can ``from fastmcp_builder.generate import ServerAlreadyRegistered`` —
this is the import path T5 (register.py) will use as well.
"""
from __future__ import annotations

import ast
import dataclasses
import importlib
import importlib.util
import json
import keyword
import re
import sys
import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal, Optional

from .errors import (
    ClassNotFound,
    DuplicateToolName,
    GenerateError,
    InvalidIdentifier,
    InvalidSlug,
    MalformedConfig,
    MethodNotFound,
    OutsideProjectRoot,
    ServerAlreadyRegistered,
    SignatureMismatch,
    UnsupportedClassType,
)

__all__ = [
    "Param",
    "ToolSpec",
    "ServerSpec",
    "generate_server",
    "safe_write",
    # re-exports
    "GenerateError",
    "ServerAlreadyRegistered",
    "InvalidIdentifier",
    "InvalidSlug",
    "DuplicateToolName",
    "MethodNotFound",
    "ClassNotFound",
    "UnsupportedClassType",
    "OutsideProjectRoot",
    "MalformedConfig",
    "SignatureMismatch",
]


# ---------- dataclasses (locked interface, design.md §8) ----------


@dataclass(frozen=True)
class Param:
    name: str
    type: str
    desc: str


@dataclass(frozen=True)
class ToolSpec:
    name: str
    docstring: str
    params: list[Param] = field(default_factory=list)
    return_type: str = "str"
    return_desc: str = ""
    reuse_from: Optional[str] = None
    reuse_method: Optional[str] = None


@dataclass(frozen=True)
class ServerSpec:
    name: str
    slug: str
    description: str
    transport: Literal["stdio"] = "stdio"
    tools: list[ToolSpec] = field(default_factory=list)
    env: list[str] = field(default_factory=list)
    deps: list[str] = field(default_factory=list)


# ---------- type allow-list (design.md §1) ----------

_PRIMITIVE_TYPES = frozenset(
    {
        "int",
        "float",
        "str",
        "bool",
        "list[int]",
        "list[str]",
        "list[float]",
        "list[bool]",
        "dict",
        "None",
    }
)

_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{0,39}$")


# ---------- safe_write chokepoint (design.md U9) ----------


def safe_write(path: Path, content: str, *, project_root: Path) -> Path:
    """Write ``content`` to ``path`` only if it is inside ``project_root``.

    Raises :class:`OutsideProjectRoot` for any path that escapes the root
    after resolution. This is the single chokepoint for all generator writes.
    """
    project_root = project_root.resolve()
    target = path.resolve()
    try:
        is_inside = target.is_relative_to(project_root)
    except AttributeError:  # pragma: no cover  (py<3.9)
        is_inside = str(target).startswith(str(project_root))
    if not is_inside:
        raise OutsideProjectRoot(
            f"Refusing to write outside project root: {target} is not under {project_root}"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return target


def _ensure_marker(path: Path, project_root: Path) -> None:
    """Create an empty ``__init__.py`` marker only if absent (idempotent)."""
    if path.exists():
        return
    safe_write(path, "", project_root=project_root)


# ---------- type resolution (design.md §3.B) ----------


@dataclass(frozen=True)
class _ClassRef:
    """Resolved class-type import: ``from mcp_code.<module> import <class_name>``."""

    module: str  # dotted, without leading ``mcp_code.``
    class_name: str

    @property
    def import_module(self) -> str:
        return f"mcp_code.{self.module}"


def _is_primitive_type(type_str: str) -> bool:
    return type_str in _PRIMITIVE_TYPES


def _parse_class_ref(type_str: str) -> _ClassRef:
    """Split a dotted ref like ``models.UserCreate`` or ``mcp_code.models.UserCreate``.

    Each segment before the class must be a valid Python identifier; class is
    the last segment.
    """
    raw = type_str.strip()
    if raw.startswith("mcp_code."):
        raw = raw[len("mcp_code."):]
    parts = raw.split(".")
    if len(parts) < 2:
        raise InvalidIdentifier(
            f"Class-ref type must be ``<module>.<ClassName>``, got: {type_str!r}"
        )
    for seg in parts:
        if not seg.isidentifier() or keyword.iskeyword(seg):
            raise InvalidIdentifier(
                f"Invalid segment in class ref {type_str!r}: {seg!r} is not a valid Python identifier"
            )
    module = ".".join(parts[:-1])
    class_name = parts[-1]
    return _ClassRef(module=module, class_name=class_name)


def _module_file_for(module: str, project_root: Path) -> Path:
    """Find ``mcp_code/<module>.py`` or ``mcp_code/<module>/__init__.py`` under root.

    Raises :class:`FileNotFoundError` if neither exists.
    """
    base = project_root / "mcp_code"
    rel = Path(*module.split("."))
    candidate_file = base / rel.with_suffix(".py")
    candidate_pkg = base / rel / "__init__.py"
    if candidate_file.is_file():
        return candidate_file
    if candidate_pkg.is_file():
        return candidate_pkg
    raise FileNotFoundError(
        f"Class-ref module not found: tried {candidate_file} and {candidate_pkg}"
    )


def _validate_class_ref(ref: _ClassRef, project_root: Path) -> None:
    """Validate that the class ref resolves to a Pydantic BaseModel or @dataclass.

    Steps (design.md §3.B):
      1. Module file must exist.
      2. ``importlib.import_module("mcp_code.<module>")`` must succeed and have
         the class attribute.
      3. Class must be ``pydantic.BaseModel`` subclass OR ``dataclasses.is_dataclass``.
    """
    _module_file_for(ref.module, project_root)  # may raise FileNotFoundError

    project_root_str = str(project_root.resolve())
    added_path = False
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
        added_path = True
    # Drop any cached version so we pick up the tmp project's module.
    cached = [m for m in list(sys.modules) if m == ref.import_module or m.startswith(ref.import_module + ".") or m == "mcp_code" or m.startswith("mcp_code.")]
    for m in cached:
        sys.modules.pop(m, None)

    try:
        try:
            mod = importlib.import_module(ref.import_module)
        except ImportError as exc:
            raise FileNotFoundError(
                f"Failed to import {ref.import_module!r}: {exc}"
            ) from exc

        cls = getattr(mod, ref.class_name, None)
        if cls is None:
            raise ClassNotFound(
                f"{ref.class_name!r} not found in module {ref.import_module!r}"
            )

        is_pydantic = False
        try:
            import pydantic  # type: ignore[import-not-found]

            try:
                is_pydantic = isinstance(cls, type) and issubclass(cls, pydantic.BaseModel)
            except TypeError:
                is_pydantic = False
        except ImportError:
            is_pydantic = False

        is_dc = dataclasses.is_dataclass(cls)

        if not (is_pydantic or is_dc):
            raise UnsupportedClassType(
                f"{ref.import_module}.{ref.class_name} is neither a "
                f"pydantic.BaseModel subclass nor a @dataclass — make it one or "
                f"use a primitive type."
            )
    finally:
        if added_path:
            try:
                sys.path.remove(project_root_str)
            except ValueError:
                pass


def _resolve_type_annotation(
    type_str: str, project_root: Path, class_refs: dict[str, _ClassRef]
) -> str:
    """Return the rendered annotation string.

    For primitives, returns ``type_str`` unchanged. For class refs, validates
    the class, registers the import in ``class_refs``, and returns the bare
    ``ClassName`` to use in the annotation.
    """
    if _is_primitive_type(type_str):
        return type_str
    ref = _parse_class_ref(type_str)
    _validate_class_ref(ref, project_root)
    key = f"{ref.import_module}:{ref.class_name}"
    class_refs.setdefault(key, ref)
    return ref.class_name


# ---------- reuse-method validation (design.md §3.A) ----------


def _reuse_module_for(reuse_from: str) -> str:
    """Convert ``utils.py`` / ``math/ops.py`` to ``mcp_code.utils`` / ``mcp_code.math.ops``."""
    raw = reuse_from.strip()
    if raw.startswith("mcp_code/"):
        raw = raw[len("mcp_code/"):]
    p = Path(raw)
    if p.suffix == ".py":
        p = p.with_suffix("")
    parts = p.parts
    for seg in parts:
        if not seg.isidentifier() or keyword.iskeyword(seg):
            raise InvalidIdentifier(
                f"reuse_from path segment {seg!r} is not a valid Python identifier"
            )
    return "mcp_code." + ".".join(parts)


def _validate_reuse(tool: ToolSpec, project_root: Path) -> None:
    """Validate reuse_from + reuse_method per design.md §3.A.

    Raises FileNotFoundError, MethodNotFound; emits SignatureMismatch warnings.
    """
    assert tool.reuse_from is not None and tool.reuse_method is not None

    file_path = (project_root / tool.reuse_from).resolve()
    if not file_path.is_file():
        # also try mcp_code/ prefix-stripped form
        rel = tool.reuse_from
        if rel.startswith("mcp_code/"):
            rel = rel[len("mcp_code/"):]
        alt = (project_root / "mcp_code" / rel).resolve()
        if not alt.is_file():
            raise FileNotFoundError(
                f"reuse_from file not found: {file_path}"
            )
        file_path = alt

    tree = ast.parse(file_path.read_text())
    func_node = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == tool.reuse_method:
            func_node = node
            break
    if func_node is None:
        raise MethodNotFound(
            f"Method {tool.reuse_method!r} not found in {file_path}"
        )

    # Param-name parity (warning only)
    args = [a.arg for a in func_node.args.args]
    # drop self/cls if present (paranoia — we asserted top-level def)
    spec_names = [p.name for p in tool.params]
    if args != spec_names:
        warnings.warn(
            f"Signature mismatch for {tool.name}: reuse_method args={args} "
            f"vs spec params={spec_names}",
            SignatureMismatch,
            stacklevel=2,
        )


# ---------- spec validation ----------


def _validate_spec(spec: ServerSpec) -> None:
    if not _SLUG_RE.match(spec.slug):
        raise InvalidSlug(
            f"slug {spec.slug!r} does not match ^[a-z][a-z0-9-]{{0,39}}$"
        )
    seen: set[str] = set()
    for tool in spec.tools:
        if not tool.name.isidentifier() or keyword.iskeyword(tool.name):
            raise InvalidIdentifier(
                f"Tool name {tool.name!r} is not a valid Python identifier"
            )
        if tool.name in seen:
            raise DuplicateToolName(
                f"Duplicate tool name in spec: {tool.name!r}"
            )
        seen.add(tool.name)
        param_seen: set[str] = set()
        for p in tool.params:
            if not p.name.isidentifier() or keyword.iskeyword(p.name):
                raise InvalidIdentifier(
                    f"Param name {p.name!r} (tool {tool.name!r}) is not a valid Python identifier"
                )
            if p.name in param_seen:
                raise InvalidIdentifier(
                    f"Duplicate param name {p.name!r} in tool {tool.name!r}"
                )
            param_seen.add(p.name)


# ---------- rendering helpers (f-string template) ----------


def _render_signature(tool: ToolSpec, annotations: dict[str, str], return_anno: str) -> str:
    """Render ``def name(p: T, ...) -> R:`` line."""
    params = ", ".join(f"{p.name}: {annotations[p.name]}" for p in tool.params)
    return f"def {tool.name}({params}) -> {return_anno}:"


def _render_docstring(tool: ToolSpec) -> str:
    """Render a Google-style docstring with Args/Returns sections."""
    lines: list[str] = []
    # First-line(s) of docstring as written by the guide
    doc_lines = tool.docstring.rstrip("\n").split("\n")
    lines.extend(doc_lines)
    if tool.params:
        lines.append("")
        lines.append("Args:")
        for p in tool.params:
            lines.append(f"    {p.name}: {p.desc}")
    if tool.return_desc:
        lines.append("")
        lines.append("Returns:")
        lines.append(f"    {tool.return_desc}")
    body = "\n    ".join(lines)
    return f'"""{body}\n    """'


def _render_body(tool: ToolSpec) -> str:
    """Render the function body — delegate or NotImplementedError."""
    if tool.reuse_from and tool.reuse_method:
        kwargs = ", ".join(f"{p.name}={p.name}" for p in tool.params)
        return f"return _{tool.name}_impl({kwargs})"
    return f'raise NotImplementedError("implement {tool.name}")'


def _render_tool_block(
    tool: ToolSpec,
    annotations: dict[str, str],
    return_anno: str,
) -> str:
    sig = _render_signature(tool, annotations, return_anno)
    doc = _render_docstring(tool)
    body = _render_body(tool)
    return (
        f"@mcp.tool\n"
        f"{sig}\n"
        f"    {doc}\n"
        f"    {body}\n"
    )


def _render_reuse_imports(tools: list[ToolSpec]) -> list[str]:
    out: list[str] = []
    for t in tools:
        if t.reuse_from and t.reuse_method:
            module = _reuse_module_for(t.reuse_from)
            out.append(f"from {module} import {t.reuse_method} as _{t.name}_impl")
    return out


def _render_class_imports(class_refs: dict[str, _ClassRef]) -> list[str]:
    # Group by module, dedupe class names per module, sort.
    by_module: dict[str, set[str]] = {}
    for ref in class_refs.values():
        by_module.setdefault(ref.import_module, set()).add(ref.class_name)
    lines: list[str] = []
    for module in sorted(by_module):
        names = sorted(by_module[module])
        # Single-import-per-module form (more readable than parens)
        lines.append(f"from {module} import {', '.join(names)}")
    return lines


def _render_server_py(spec: ServerSpec, project_root: Path) -> str:
    # Per-tool annotation maps + class-import collection
    class_refs: dict[str, _ClassRef] = {}
    tool_blocks: list[str] = []
    for tool in spec.tools:
        annotations: dict[str, str] = {}
        for p in tool.params:
            annotations[p.name] = _resolve_type_annotation(p.type, project_root, class_refs)
        return_anno = _resolve_type_annotation(tool.return_type, project_root, class_refs)
        if tool.reuse_from and tool.reuse_method:
            _validate_reuse(tool, project_root)
        tool_blocks.append(_render_tool_block(tool, annotations, return_anno))

    parts: list[str] = []
    parts.append(f'"""{spec.description}"""')
    parts.append("")
    parts.append("from fastmcp import FastMCP")

    class_import_lines = _render_class_imports(class_refs)
    if class_import_lines:
        parts.extend(class_import_lines)

    reuse_lines = _render_reuse_imports(spec.tools)
    if reuse_lines:
        parts.extend(reuse_lines)

    parts.append("")
    parts.append(f'mcp = FastMCP(name="{spec.name}")')
    parts.append("")
    parts.append("")
    parts.append("\n\n".join(tool_blocks).rstrip("\n"))
    parts.append("")
    parts.append("")
    parts.append('if __name__ == "__main__":')
    parts.append("    mcp.run()")
    parts.append("")

    return "\n".join(parts)


def _spec_to_jsonable(spec: ServerSpec) -> dict:
    return asdict(spec)


# ---------- public entry point ----------


def generate_server(
    spec: ServerSpec,
    project_root: Path,
    overwrite: bool = False,
) -> Path:
    """Write ``mcp_code/<slug>/server.py`` and ``spec.json``. Returns server.py path.

    See module docstring and design.md §3 / §6 / §8 for the contract.
    """
    project_root = Path(project_root).resolve()
    _validate_spec(spec)

    target_dir = project_root / "mcp_code" / spec.slug
    target_path = target_dir / "server.py"

    if target_path.exists() and not overwrite:
        raise ServerAlreadyRegistered(
            f"Server already exists at {target_path}; pass overwrite=True to replace."
        )

    # Render first — fail before touching disk (idempotent on errors).
    rendered = _render_server_py(spec, project_root)

    # Package markers (idempotent)
    _ensure_marker(project_root / "mcp_code" / "__init__.py", project_root)
    _ensure_marker(target_dir / "__init__.py", project_root)

    # server.py
    safe_write(target_path, rendered, project_root=project_root)

    # spec sidecar
    sidecar = target_dir / "spec.json"
    payload = {"version": 1, "spec": _spec_to_jsonable(spec)}
    safe_write(
        sidecar,
        json.dumps(payload, indent=2) + "\n",
        project_root=project_root,
    )

    return target_path
