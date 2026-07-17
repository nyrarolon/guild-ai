"""Result verification utilities for Guild AI quests.

Verifies agent capability claims, result schema conformance,
and proof-of-computation hashes. Pure functions, no side effects.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def verify_capability(agent_manifest: dict, required: list[str]) -> bool:
    """Check that an agent manifest declares all required capabilities.

    Parameters
    ----------
    agent_manifest : dict
        The agent's capability manifest, expected to have a 'capabilities' key
        containing a list of capability strings.
    required : list[str]
        Capabilities the quest requires.

    Returns
    -------
    bool
        True if the agent has all required capabilities.
    """
    declared = set(agent_manifest.get("capabilities", []))
    return all(req in declared for req in required)


def verify_schema(result: dict, schema: dict) -> bool:
    """Check that *result* conforms to *schema*.

    Schema is a dict mapping field names to expected Python type names
    (e.g. ``{"price": "float", "symbol": "str"}``).  For each field:

    *   The field must exist in ``result``.
    *   Its value's type must match the schema type string using
        :func:`_type_matches`.

    Nested schemas (dict-of-dict) are supported recursively.

    Parameters
    ----------
    result : dict
        The result payload to validate.
    schema : dict
        Type-checking schema.

    Returns
    -------
    bool
    """
    for field, expected in schema.items():
        if field not in result:
            return False
        if isinstance(expected, dict):
            # Nested object
            if not isinstance(result[field], dict):
                return False
            if not verify_schema(result[field], expected):
                return False
        else:
            if not _type_matches(result[field], expected):
                return False
    return True


def verify_proof_hash(data: dict, claimed_hash: str) -> bool:
    """Verify that a SHA-256 hash of the canonical JSON of *data*
    matches *claimed_hash*.

    "Canonical" here means keys sorted alphabetically for deterministic
    serialisation.

    Parameters
    ----------
    data : dict
        The data that was hashed.
    claimed_hash : str
        The hex-encoded SHA-256 hash to verify against.

    Returns
    -------
    bool
    """
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return actual == claimed_hash


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TYPE_MAP: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "dict": dict,
    "list": list,
}


def _type_matches(value: Any, expected_type_name: str) -> bool:
    """Return True if *value* is an instance of the type named by
    *expected_type_name* (case-insensitive).

    Supports simple names (``str``, ``int``, ``float``, ``bool``, ``dict``,
    ``list``) and two sugar forms:

    *   ``"float"`` also accepts ``int`` values (widening).
    *   If the expected name ends with ``[]`` (e.g. ``"int[]"``) the value
        must be a list whose every element matches the inner type.
    """
    name = expected_type_name.strip().lower()

    # List-of-X sugar:  "int[]", "str[]"
    if name.endswith("[]"):
        inner = name[:-2]
        if not isinstance(value, list):
            return False
        return all(_type_matches(item, inner) for item in value)

    # Nullable — allow None for any typed field
    if value is None:
        return True

    # Float accepts int
    if name == "float" and isinstance(value, (int, float)):
        return True

    expected = _TYPE_MAP.get(name)
    if expected is None:
        # Unknown type name — skip validation
        return True
    return isinstance(value, expected)
