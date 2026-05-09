"""Exception hierarchy for fastmcp_builder.

This module is the canonical home for the builder's error classes. Both
``generate.py`` (T4) and ``register.py`` (T5) import from here so callers
have one stable place to catch.
"""
from __future__ import annotations


class GenerateError(Exception):
    """Base class for any failure raised by the generator."""


class ServerAlreadyRegistered(GenerateError):
    """Raised when a server file/entry already exists and overwrite is False.

    Used by both ``generate_server`` (file collision) and
    ``register_project_scope`` (.mcp.json key collision).
    """


class InvalidIdentifier(GenerateError):
    """A name that must be a valid Python identifier was not."""


class InvalidSlug(GenerateError):
    """A slug failed the ``^[a-z][a-z0-9-]{0,39}$`` regex."""


class DuplicateToolName(GenerateError):
    """Two tools in one server share a name."""


class MethodNotFound(GenerateError):
    """A reuse_method could not be found in the reuse_from file."""


class ClassNotFound(GenerateError):
    """A dotted class ref module exists but the class attribute is missing."""


class UnsupportedClassType(GenerateError):
    """A class ref resolves to neither a Pydantic BaseModel nor a dataclass."""


class OutsideProjectRoot(GenerateError):
    """A write was attempted at a path outside the project root."""


class MalformedConfig(GenerateError):
    """Existing .mcp.json is not valid JSON. (Used by T5; declared here for stability.)"""


class SecretLiteralRefused(GenerateError):
    """A literal secret value was passed where a ${VAR} placeholder is required.

    Raised by ``register_project_scope`` when an env-var key matches the
    secret heuristic regex but its value is not in the form ``${VAR}``.
    """


class SignatureMismatch(Warning):
    """Reuse-method signature does not line up with the tool spec.

    Emitted as a warning (via ``warnings.warn``) — never raised.
    """
