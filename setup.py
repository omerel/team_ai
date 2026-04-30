"""Team-AI Multi-Agent Framework scaffolder."""
import re

NICKNAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
RESERVED_NICKNAMES = frozenset({
    "general-purpose",
    "Explore",
    "Plan",
    "code-simplifier",
    "statusline-setup",
})


class NicknameError(ValueError):
    """Raised when a nickname fails validation."""


def validate_nickname(nickname: str, existing: set) -> None:
    """Validate a nickname. Raises NicknameError on failure."""
    if not nickname:
        raise NicknameError("nickname cannot be empty")
    if not NICKNAME_PATTERN.match(nickname):
        raise NicknameError(
            f"invalid nickname '{nickname}': must be 2-31 chars, "
            "lowercase, start with a letter, only [a-z0-9-]"
        )
    if nickname in RESERVED_NICKNAMES:
        raise NicknameError(
            f"'{nickname}' is reserved and cannot be used as a nickname"
        )
    if nickname in existing:
        raise NicknameError(
            f"nickname '{nickname}' is already taken by another agent"
        )


SLUG_MAX_LEN = 40


def slugify(text: str) -> str:
    """Convert free-form text into a sprint folder slug.

    Lowercase, alphanumeric and hyphens only, max 40 characters.
    Falls back to 'sprint' when input has no usable characters.
    """
    lowered = text.lower()
    # remove non-ascii characters
    ascii_only = lowered.encode('ascii', 'ignore').decode('ascii')
    # replace any non-[a-z0-9] with a hyphen
    cleaned = re.sub(r"[^a-z0-9]+", "-", ascii_only)
    cleaned = cleaned.strip("-")
    if not cleaned:
        return "sprint"
    if len(cleaned) > SLUG_MAX_LEN:
        cleaned = cleaned[:SLUG_MAX_LEN].rstrip("-")
    return cleaned or "sprint"


from string import Template


class RenderError(ValueError):
    """Raised when a template references an unprovided variable."""


def render_template(text: str, mapping: dict) -> str:
    """Render a string.Template with the given mapping.

    Raises RenderError if the template references a variable
    not present in the mapping. Uses safe $var / ${var} syntax;
    $$ is the literal-dollar escape.
    """
    try:
        return Template(text).substitute(mapping)
    except KeyError as e:
        raise RenderError(f"template references undefined variable: {e}") from e
    except ValueError as e:
        raise RenderError(f"invalid template syntax: {e}") from e


import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------

# Each entry: role -> (default description, default nickname)
AGENTS = {
    "planner": ("Breaks sprint goals into structured plans with per-task assignments.", "planner"),
    "reviewer": ("Independent QA gate; verifies completed work against acceptance criteria.", "reviewer"),
    "researcher": ("Reads resources and external sources; synthesizes findings.", "researcher"),
    "architect": ("Owns system design, tech stack, and module boundaries.", "architect"),
    "implementer": ("Generic builder; default executor for code tasks.", "implementer"),
    "backend-specialist": ("APIs, services, data layer, server-side logic.", "backend"),
    "frontend-specialist": ("UI/UX implementation; components, styling, client state.", "frontend"),
    "qa-engineer": ("Test design and execution; behavioral validation.", "qa"),
    "devops": ("CI/CD, deployment, infrastructure, build pipelines.", "devops"),
    "documenter": ("READMEs, API docs, user guides, changelog.", "documenter"),
    "data-ml-engineer": ("Data pipelines and ML model code paths.", "ml"),
    "security-reviewer": ("Audits code for security risks.", "security"),
}

CORE_AGENTS = ("planner", "reviewer")
MINIMAL_AGENTS = (
    "planner", "reviewer", "researcher", "architect",
    "implementer", "qa-engineer", "documenter",
)

REPO_ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = REPO_ROOT / "template"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="setup.py",
        description="Team-AI: scaffold a multi-agent project workspace.",
    )
    p.add_argument("target", nargs="?", help="Target project directory (for scaffold mode)")
    p.add_argument("--minimal", action="store_true", help="Non-interactive scaffold with defaults")
    p.add_argument("--force", action="store_true", help="Overwrite an existing .claude/")
    # In-place ops (run from inside a generated project; require a target with .claude/team.md)
    p.add_argument("--list-team", action="store_true", help="Print the team roster")
    p.add_argument("--rename", metavar="OLD=NEW", help="Rename an agent nickname")
    p.add_argument("--add-agent", metavar="ROLE", help="Add an agent by role")
    p.add_argument("--remove-agent", metavar="NICKNAME", help="Remove an agent by nickname")
    return p


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    in_place_flags = (args.list_team, args.rename, args.add_agent, args.remove_agent)
    if any(in_place_flags):
        # In-place ops use cwd as the project root unless target is given.
        project = Path(args.target).resolve() if args.target else Path.cwd()
        if args.list_team:
            return list_team(project)
        if args.rename:
            return rename_agent(project, args.rename)
        if args.add_agent:
            return add_agent(project, args.add_agent)
        if args.remove_agent:
            return remove_agent(project, args.remove_agent)

    # Scaffold mode
    if not args.target:
        parser.error("target directory is required for scaffold mode")
    target = Path(args.target).resolve()
    return scaffold_project(target, minimal=args.minimal, force=args.force)


# Stubs — implemented in later tasks
def scaffold_project(target: Path, minimal: bool = False, force: bool = False) -> int:
    raise NotImplementedError("scaffold_project: implemented in Task 17")


def list_team(project: Path) -> int:
    raise NotImplementedError("list_team: implemented in Task 20")


def rename_agent(project: Path, spec: str) -> int:
    raise NotImplementedError("rename_agent: implemented in Task 21")


def add_agent(project: Path, role: str) -> int:
    raise NotImplementedError("add_agent: implemented in Task 22")


def remove_agent(project: Path, nickname: str) -> int:
    raise NotImplementedError("remove_agent: implemented in Task 23")


if __name__ == "__main__":
    sys.exit(main())
