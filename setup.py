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
