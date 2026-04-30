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
