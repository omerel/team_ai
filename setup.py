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
import shutil
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _render_roster_block(roster: dict) -> str:
    """Render the team.md roster block from {role: nickname} mapping."""
    lines = []
    for role, nickname in roster.items():
        desc = AGENTS[role][0]
        lines.append(f"- **@{nickname}** — {role}: {desc}")
    return "\n".join(lines)


def _copy_dir(src: Path, dst: Path) -> None:
    """Copy a directory tree, replacing dst if it exists."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def scaffold_project(target: Path, minimal: bool = False, force: bool = False) -> int:
    """Scaffold a new team-ai project at `target`.

    `minimal=True` skips the wizard and uses MINIMAL_AGENTS with default nicknames.
    `force=True` removes any existing .claude/ at target before scaffolding.
    Returns 0 on success.
    """
    claude_dir = target / ".claude"
    if claude_dir.exists() and not force:
        sys.stderr.write(
            f"error: {claude_dir} already exists. Use --force to overwrite.\n"
        )
        sys.exit(1)
    if claude_dir.exists() and force:
        shutil.rmtree(claude_dir)

    if minimal:
        project_name = target.name
        description = ""
        roster = {role: AGENTS[role][1] for role in MINIMAL_AGENTS}
    else:
        project_name, description, roster = run_wizard(target)

    target.mkdir(parents=True, exist_ok=True)
    (target / "src").mkdir(exist_ok=True)
    (target / "resource").mkdir(exist_ok=True)
    (target / "sprints").mkdir(exist_ok=True)
    (target / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
    (target / ".claude" / "commands").mkdir(exist_ok=True)
    (target / ".claude" / "scripts").mkdir(exist_ok=True)

    # Render CLAUDE.md
    claude_tmpl = (TEMPLATE_DIR / "CLAUDE.md.tmpl").read_text()
    (target / "CLAUDE.md").write_text(
        render_template(claude_tmpl, {
            "project_name": project_name,
            "description": description or "(no description provided)",
        })
    )

    # Render team.md
    team_tmpl = (TEMPLATE_DIR / "claude" / "team.md.tmpl").read_text()
    (target / ".claude" / "team.md").write_text(
        render_template(team_tmpl, {
            "project_name": project_name,
            "roster_block": _render_roster_block(roster),
        })
    )

    # Copy settings.json
    shutil.copy(
        TEMPLATE_DIR / "claude" / "settings.json",
        target / ".claude" / "settings.json",
    )

    # Resource README
    shutil.copy(
        TEMPLATE_DIR / "resource_README.md",
        target / "resource" / "README.md",
    )

    # Slash commands (no rendering — copy as-is)
    cmd_src = TEMPLATE_DIR / "claude" / "commands"
    cmd_dst = target / ".claude" / "commands"
    for f in cmd_src.glob("*.md"):
        shutil.copy(f, cmd_dst / f.name)

    # Skills (verbatim copy)
    _copy_dir(TEMPLATE_DIR / "claude" / "skills", target / ".claude" / "skills")

    # Render each installed agent
    for role, nickname in roster.items():
        tmpl_path = TEMPLATE_DIR / "claude" / "agents" / f"{role}.md.tmpl"
        if not tmpl_path.exists():
            sys.stderr.write(f"error: missing agent template {tmpl_path}\n")
            sys.exit(2)
        rendered = render_template(tmpl_path.read_text(), {
            "nickname": nickname,
            "project_name": project_name,
        })
        (target / ".claude" / "agents" / f"{role}.md").write_text(rendered)

    # Copy setup.py itself for in-place ops
    shutil.copy(REPO_ROOT / "setup.py", target / ".claude" / "scripts" / "team_setup.py")

    print(f"✓ Project scaffolded at {target}")
    print("  Next: drop knowledge into resource/, then run /sprint-start \"<goal>\"")
    return 0


def _ask(prompt: str, default: str = "") -> str:
    """Prompt the user; return the answer or the default if blank."""
    suffix = f" [{default}]" if default else ""
    raw = input(f"{prompt}{suffix}: ").strip()
    return raw or default


def _ask_yes_no(prompt: str, default_no: bool = True) -> bool:
    """Yes/no prompt. Returns True for yes, False for no."""
    default = "n" if default_no else "y"
    while True:
        raw = input(f"{prompt} (y/n) [{default}]: ").strip().lower() or default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  please answer y or n")


def _ask_nickname(role: str, default: str, existing: set) -> str:
    """Prompt for a nickname, retrying until validation passes."""
    while True:
        candidate = _ask(f"  Nickname for {role}", default=default)
        try:
            validate_nickname(candidate, existing=existing)
            return candidate
        except NicknameError as e:
            print(f"  ✗ {e}")


def run_wizard(target: Path):
    """Interactive wizard. Returns (project_name, description, roster_dict)."""
    print()
    print("=" * 60)
    print(" Team-AI scaffolder — interactive setup")
    print("=" * 60)
    print()

    project_name = _ask("Project name", default=target.name)
    description = _ask("One-line description", default="")

    print()
    print("Specialist selection — pick which agents to install.")
    print("(Core agents 'planner' and 'reviewer' are always installed.)")
    print()

    installed_roles = list(CORE_AGENTS)
    for role in AGENTS:
        if role in CORE_AGENTS:
            continue
        desc = AGENTS[role][0]
        print(f"  {role}: {desc}")
        if _ask_yes_no(f"  Install {role}?", default_no=True):
            installed_roles.append(role)
        print()

    print()
    print("Nicknames — give each agent a name (or accept the default).")
    print()
    roster = {}
    used = set()
    for role in installed_roles:
        default = AGENTS[role][1]
        nickname = _ask_nickname(role, default, used)
        roster[role] = nickname
        used.add(nickname)

    print()
    print("Roster summary:")
    for role, nickname in roster.items():
        print(f"  @{nickname} — {role}")
    print()
    if not _ask_yes_no("Proceed with this roster?", default_no=False):
        print("Aborted.")
        sys.exit(1)

    return project_name, description, roster


def _require_project(project: Path) -> Path:
    """Verify `project` is a generated team-ai project. Returns path to team.md."""
    team_md = project / ".claude" / "team.md"
    if not team_md.is_file():
        sys.stderr.write(
            f"error: {project} is not a team-ai project (no .claude/team.md)\n"
        )
        sys.exit(1)
    return team_md


def list_team(project: Path) -> int:
    """Print the team.md contents."""
    team_md = _require_project(project)
    print(team_md.read_text())
    return 0


def rename_agent(project: Path, spec: str) -> int:
    raise NotImplementedError("rename_agent: implemented in Task 21")


def add_agent(project: Path, role: str) -> int:
    raise NotImplementedError("add_agent: implemented in Task 22")


def remove_agent(project: Path, nickname: str) -> int:
    raise NotImplementedError("remove_agent: implemented in Task 23")


if __name__ == "__main__":
    sys.exit(main())
