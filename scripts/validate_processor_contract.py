#!/usr/bin/env python3
"""Validate that Python Pydantic models match the engine.proto contract.

Parses proto/engine/v1/engine.proto and verifies that the ProcessLLMResponse
fields match ProcessorOutput in src/engine/processor/models/io.py.

The engine.proto is the SINGLE SOURCE OF TRUTH for the contract between
the Go gateway and the Python engine. Both sides must stay in sync.

Run this in CI to catch drift before it reaches production:
    python scripts/validate_processor_contract.py
    # or: make contract-check

Exit code 0 = all fields match.
Exit code 1 = drift detected.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Proto field name -> Python field name mapping.
# Proto uses bytes for JSON-encoded fields, Python uses dict.
PROTO_TO_PYTHON_FIELD_MAP: dict[str, str] = {
    "raw_response_json": "raw_response",
}

# Proto message name -> Python class name mapping.
PROTO_TO_PYTHON_CLASS_MAP: dict[str, str] = {
    "ProcessLLMResponse": "ProcessorOutput",
}


def parse_proto_messages(proto_path: Path) -> dict[str, list[str]]:
    """Parse a .proto file and extract message field names.

    Returns a dict of {message_name: [field_names]}.
    """
    content = proto_path.read_text()
    messages: dict[str, list[str]] = {}

    # Match message blocks.
    msg_pattern = re.compile(r"message\s+(\w+)\s*\{([^}]+)\}", re.DOTALL)
    # Match field declarations: type name = number;
    field_pattern = re.compile(
        r"^\s*(?:repeated\s+)?(?:map<[^>]+>|\w+)\s+(\w+)\s*=\s*\d+\s*;",
        re.MULTILINE,
    )

    for msg_match in msg_pattern.finditer(content):
        msg_name = msg_match.group(1)
        msg_body = msg_match.group(2)
        fields = field_pattern.findall(msg_body)
        messages[msg_name] = fields

    return messages


def get_pydantic_fields(class_name: str, module_path: Path) -> set[str]:
    """Extract field names from a Pydantic model class in a Python file.

    Uses regex parsing (not import) to avoid dependency issues in CI.
    """
    content = module_path.read_text()

    # Find the class block.
    class_pattern = re.compile(
        rf"class\s+{class_name}\s*\([^)]*\)\s*:",
    )
    match = class_pattern.search(content)
    if not match:
        return set()

    # Extract fields from the class body (lines with : type annotation).
    start = match.end()
    fields: set[str] = set()

    # Pydantic/base-class attributes that are NOT proto contract fields.
    IGNORED_FIELDS = {"Proto", "model_config", "model_fields", "model_computed_fields"}

    for line in content[start:].split("\n"):
        stripped = line.strip()
        # Stop at next class definition or top-level function.
        if stripped and not stripped.startswith("#") and not stripped.startswith('"""'):
            if re.match(r"^class\s+", stripped) or re.match(r"^def\s+", stripped):
                break
            # Match field: type = ... or field: type patterns.
            field_match = re.match(r"^(\w+)\s*:\s*", stripped)
            if field_match:
                field_name = field_match.group(1)
                # Skip dunder, private, and Pydantic internal fields.
                if not field_name.startswith("_") and field_name not in IGNORED_FIELDS:
                    fields.add(field_name)

    return fields


def map_proto_field_to_python(proto_field: str) -> str:
    """Map a proto field name to its expected Python field name."""
    return PROTO_TO_PYTHON_FIELD_MAP.get(proto_field, proto_field)


def validate() -> bool:
    """Run the full validation. Returns True if all checks pass."""
    repo_root = Path(__file__).resolve().parent.parent
    proto_path = repo_root / "proto" / "engine" / "v1" / "engine.proto"
    python_path = repo_root / "src" / "engine" / "processor" / "models" / "io.py"

    if not proto_path.exists():
        return False

    if not python_path.exists():
        return False

    proto_messages = parse_proto_messages(proto_path)
    all_ok = True

    # Validate ProcessLLMResponse <-> ProcessorOutput
    validations = [
        ("ProcessLLMResponse", "ProcessorOutput"),
    ]

    for proto_msg_name, python_class_name in validations:
        if proto_msg_name not in proto_messages:
            all_ok = False
            continue

        proto_fields = proto_messages[proto_msg_name]
        python_fields = get_pydantic_fields(python_class_name, python_path)

        if not python_fields:
            all_ok = False
            continue

        # Check every proto field has a Python equivalent.
        expected_python_fields = {map_proto_field_to_python(f) for f in proto_fields}

        missing_in_python = expected_python_fields - python_fields
        extra_in_python = python_fields - expected_python_fields

        if missing_in_python:
            all_ok = False

        if extra_in_python:
            all_ok = False

        if not missing_in_python and not extra_in_python:
            pass

    return all_ok


if __name__ == "__main__":
    ok = validate()
    if ok:
        sys.exit(0)
    else:
        sys.exit(1)
