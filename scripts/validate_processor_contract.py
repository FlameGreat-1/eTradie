#!/usr/bin/env python3
"""Validate that Python Pydantic models match the processor proto contract.

Parses proto/processor/v1/processor.proto and verifies that every field
in ProcessorInput and ProcessorOutput has a corresponding field in the
Python Pydantic models at src/engine/processor/models/io.py.

Run this in CI to catch contract drift before it reaches production:
    python scripts/validate_processor_contract.py

Exit code 0 = all fields match.
Exit code 1 = drift detected (fields missing or mismatched).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Proto field name -> Python field name mapping.
# Proto uses snake_case, Python uses snake_case, so most map 1:1.
# Fields ending in _json in proto map to dict fields in Python
# (the proto uses bytes for JSON-encoded maps, Python uses dict).
PROTO_TO_PYTHON_FIELD_MAP: dict[str, str] = {
    "ta_analysis_json": "ta_analysis",
    "macro_analysis_json": "macro_analysis",
    "retrieved_knowledge_json": "retrieved_knowledge",
    "metadata_json": "metadata",
    "raw_response_json": "raw_response",
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
        r"^\s*(?:repeated\s+)?\w+\s+(\w+)\s*=\s*\d+\s*;",
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
                # Skip dunder and private fields.
                if not field_name.startswith("_"):
                    fields.add(field_name)

    return fields


def map_proto_field_to_python(proto_field: str) -> str:
    """Map a proto field name to its expected Python field name."""
    return PROTO_TO_PYTHON_FIELD_MAP.get(proto_field, proto_field)


def validate() -> bool:
    """Run the full validation. Returns True if all checks pass."""
    repo_root = Path(__file__).resolve().parent.parent
    proto_path = repo_root / "proto" / "processor" / "v1" / "processor.proto"
    python_path = repo_root / "src" / "engine" / "processor" / "models" / "io.py"

    if not proto_path.exists():
        print(f"ERROR: Proto file not found: {proto_path}")
        return False

    if not python_path.exists():
        print(f"ERROR: Python models file not found: {python_path}")
        return False

    proto_messages = parse_proto_messages(proto_path)
    all_ok = True

    for msg_name in ["ProcessorInput", "ProcessorOutput"]:
        if msg_name not in proto_messages:
            print(f"ERROR: Message {msg_name} not found in proto file")
            all_ok = False
            continue

        proto_fields = proto_messages[msg_name]
        python_fields = get_pydantic_fields(msg_name, python_path)

        if not python_fields:
            print(f"ERROR: Class {msg_name} not found in Python models")
            all_ok = False
            continue

        # Check every proto field has a Python equivalent.
        expected_python_fields = {
            map_proto_field_to_python(f) for f in proto_fields
        }

        missing_in_python = expected_python_fields - python_fields
        extra_in_python = python_fields - expected_python_fields

        if missing_in_python:
            print(
                f"DRIFT: {msg_name} - fields in proto but missing in Python: "
                f"{sorted(missing_in_python)}"
            )
            all_ok = False

        if extra_in_python:
            print(
                f"DRIFT: {msg_name} - fields in Python but missing in proto: "
                f"{sorted(extra_in_python)}"
            )
            all_ok = False

        if not missing_in_python and not extra_in_python:
            print(f"OK: {msg_name} - {len(proto_fields)} fields match")

    return all_ok


if __name__ == "__main__":
    print("Validating processor contract (proto <-> Python)...")
    print()
    ok = validate()
    print()
    if ok:
        print("All processor contract checks passed.")
        sys.exit(0)
    else:
        print("FAILED: Processor contract drift detected!")
        print("Update the proto and both implementations to match.")
        sys.exit(1)
