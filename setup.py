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
import json
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
    p.add_argument("--with-obsidian", action="store_true",
                   help="Include the opt-in Obsidian knowledge-vault module")
    # In-place ops (run from inside a generated project; require a target with .claude/team.md)
    p.add_argument("--list-team", action="store_true", help="Print the team roster")
    p.add_argument("--rename", metavar="OLD=NEW", help="Rename an agent nickname")
    p.add_argument("--add-agent", metavar="ROLE", help="Add an agent by role")
    p.add_argument("--remove-agent", metavar="NICKNAME", help="Remove an agent by nickname")
    p.add_argument("--add-obsidian", action="store_true",
                   help="Add the Obsidian module to an existing project (in-place)")
    return p


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    in_place_flags = (args.list_team, args.rename, args.add_agent, args.remove_agent, args.add_obsidian)
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
        if args.add_obsidian:
            return add_obsidian(project)

    # Scaffold mode
    if not args.target:
        parser.error("target directory is required for scaffold mode")
    target = Path(args.target).resolve()
    return scaffold_project(target, minimal=args.minimal, force=args.force,
                            obsidian=args.with_obsidian)


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


def scaffold_project(target: Path, minimal: bool = False, force: bool = False, obsidian: bool = False) -> int:
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
        project_name, description, roster, wiz_obsidian = run_wizard(target)
        obsidian = obsidian or wiz_obsidian

    obsidian_vars = _obsidian_vars(obsidian)

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
            **obsidian_vars,
        })
    )

    # Render team.md
    team_tmpl = (TEMPLATE_DIR / "claude" / "team.md.tmpl").read_text()
    (target / ".claude" / "team.md").write_text(
        render_template(team_tmpl, {
            "project_name": project_name,
            "roster_block": _render_roster_block(roster),
            **obsidian_vars,
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
            **obsidian_vars,
        })
        (target / ".claude" / "agents" / f"{role}.md").write_text(rendered)

    # Copy setup.py itself for in-place ops
    shutil.copy(REPO_ROOT / "setup.py", target / ".claude" / "scripts" / "team_setup.py")

    # Sprint-board generator + HTML template (offline kanban view)
    scripts_src = TEMPLATE_DIR / "claude" / "scripts"
    scripts_dst = target / ".claude" / "scripts"
    shutil.copy(scripts_src / "board.py", scripts_dst / "board.py")
    shutil.copy(
        scripts_src / "sprint-board.template.html",
        scripts_dst / "sprint-board.template.html",
    )

    # Copy templates the in-place ops need (rename re-renders team.md;
    # add-agent re-renders agent files). Exclude skills/ (already at
    # .claude/skills/) and scripts/ (board.py is copied directly above).
    template_dst = target / ".claude" / "scripts" / "template"
    if template_dst.exists():
        shutil.rmtree(template_dst)

    def _bundle_ignore(dir_path, names):
        # Strip only template/claude/skills and template/claude/scripts;
        # keep everything under template/optional/.
        dp = Path(dir_path)
        if dp.name == "claude" and dp.parent == TEMPLATE_DIR:
            return {n for n in names if n in ("skills", "scripts")}
        return set()

    shutil.copytree(TEMPLATE_DIR, template_dst, ignore=_bundle_ignore)

    if obsidian:
        apply_obsidian_module(target)

    print(f"✓ Project scaffolded at {target}")
    print("  Next: drop knowledge into resource/, then run /sprint-start \"<goal>\"")
    if obsidian:
        print("  Obsidian module added — run "
              "`.claude/scripts/setup-vault.sh` to wire up the Obsidian app.")
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
    """Interactive wizard.

    Returns (project_name, description, roster_dict, obsidian).
    """
    print()
    print("=" * 60)
    print(" Team-AI scaffolder — interactive setup")
    print("=" * 60)
    print()

    project_name = _ask("Project name", default=target.name)
    description = _ask("One-line description", default="")

    obsidian = _ask_yes_no(
        "Include the Obsidian knowledge-vault module?", default_no=True)

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

    return project_name, description, roster, obsidian


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


def _read_team_roster(project: Path) -> dict:
    """Parse the @nickname → role mapping from .claude/team.md.

    Returns dict of {role: nickname}. Looks for lines matching:
    `- **@<nickname>** — <role>: <description>`
    """
    text = (project / ".claude" / "team.md").read_text()
    roster = {}
    pattern = re.compile(r"^\-\s+\*\*@([a-z0-9-]+)\*\*\s+—\s+([a-z0-9-]+):", re.MULTILINE)
    for m in pattern.finditer(text):
        nickname, role = m.group(1), m.group(2)
        roster[role] = nickname
    return roster


def _write_team_md(project: Path, project_name: str, roster: dict,
                   obsidian_vars: dict = None) -> None:
    team_tmpl = (TEMPLATE_DIR / "claude" / "team.md.tmpl").read_text()
    (project / ".claude" / "team.md").write_text(
        render_template(team_tmpl, {
            "project_name": project_name,
            "roster_block": _render_roster_block(roster),
            **(obsidian_vars if obsidian_vars is not None else _obsidian_vars(False)),
        })
    )


def _project_name(project: Path) -> str:
    """Extract project name from the first line of CLAUDE.md (`# <name> — Team Workflow`)."""
    text = (project / "CLAUDE.md").read_text()
    m = re.match(r"^#\s+(.+?)\s+—", text)
    return m.group(1) if m else project.name


def rename_agent(project: Path, spec: str) -> int:
    """Rename an agent: spec is 'old=new'."""
    _require_project(project)
    if "=" not in spec:
        sys.stderr.write(f"error: --rename expects OLD=NEW, got '{spec}'\n")
        sys.exit(1)
    old, new = spec.split("=", 1)
    old, new = old.strip(), new.strip()

    roster = _read_team_roster(project)
    role_to_rename = None
    for role, nick in roster.items():
        if nick == old:
            role_to_rename = role
            break
    if role_to_rename is None:
        sys.stderr.write(f"error: no agent with nickname '{old}'\n")
        sys.exit(1)

    existing = set(roster.values()) - {old}
    try:
        validate_nickname(new, existing=existing)
    except NicknameError as e:
        sys.stderr.write(f"error: {e}\n")
        sys.exit(1)

    agent_file = project / ".claude" / "agents" / f"{role_to_rename}.md"
    if not agent_file.exists():
        sys.stderr.write(f"error: agent file missing: {agent_file}\n")
        sys.exit(2)
    text = agent_file.read_text()
    text = re.sub(r"^name:\s*" + re.escape(old) + r"\s*$", f"name: {new}", text, flags=re.MULTILINE)
    text = re.sub(r"\b" + re.escape(old) + r"\b", new, text)
    agent_file.write_text(text)

    roster[role_to_rename] = new
    _write_team_md(project, _project_name(project), roster)

    for sprint_dir in (project / "sprints").glob("*/"):
        wl = sprint_dir / "work-logs" / f"{old}.md"
        if wl.is_file():
            wl.rename(sprint_dir / "work-logs" / f"{new}.md")

    print(f"✓ Renamed @{old} → @{new}")
    return 0


def add_agent(project: Path, spec: str) -> int:
    """Add an agent to an existing project. Spec: 'role' or 'role=nickname'."""
    _require_project(project)

    if "=" in spec:
        role, nickname = spec.split("=", 1)
        role, nickname = role.strip(), nickname.strip()
    else:
        role = spec.strip()
        nickname = None

    if role not in AGENTS:
        sys.stderr.write(
            f"error: unknown role '{role}'. Known: {', '.join(sorted(AGENTS))}\n"
        )
        sys.exit(1)

    roster = _read_team_roster(project)
    if role in roster:
        print(f"  @{roster[role]} ({role}) is already on the team. No change.")
        return 0

    used = set(roster.values())
    if nickname is None:
        default = AGENTS[role][1]
        if default in used:
            default = ""
        nickname = _ask_nickname(role, default, used)
    else:
        try:
            validate_nickname(nickname, existing=used)
        except NicknameError as e:
            sys.stderr.write(f"error: {e}\n")
            sys.exit(1)

    tmpl_path = TEMPLATE_DIR / "claude" / "agents" / f"{role}.md.tmpl"
    if not tmpl_path.exists():
        sys.stderr.write(f"error: missing agent template {tmpl_path}\n")
        sys.exit(2)
    project_name = _project_name(project)
    rendered = render_template(tmpl_path.read_text(), {
        "nickname": nickname,
        "project_name": project_name,
        **_obsidian_vars(False),
    })
    (project / ".claude" / "agents" / f"{role}.md").write_text(rendered)

    roster[role] = nickname
    _write_team_md(project, project_name, roster)

    print(f"✓ Added @{nickname} ({role}) to the team")
    return 0


def remove_agent(project: Path, nickname: str) -> int:
    """Remove an agent by nickname. Refuses to remove core agents."""
    _require_project(project)
    nickname = nickname.strip()

    roster = _read_team_roster(project)
    role_to_remove = None
    for role, nick in roster.items():
        if nick == nickname:
            role_to_remove = role
            break
    if role_to_remove is None:
        sys.stderr.write(f"error: no agent with nickname '{nickname}'\n")
        sys.exit(1)

    if role_to_remove in CORE_AGENTS:
        sys.stderr.write(
            f"error: '{role_to_remove}' is a core agent and cannot be removed.\n"
        )
        sys.exit(1)

    agent_file = project / ".claude" / "agents" / f"{role_to_remove}.md"
    if agent_file.exists():
        agent_file.unlink()

    del roster[role_to_remove]
    _write_team_md(project, _project_name(project), roster)

    print(f"✓ Removed @{nickname} ({role_to_remove}) from the team")
    return 0


if __name__ == "__main__":
    sys.exit(main())
