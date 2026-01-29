#!/usr/bin/env python3
"""Validate senior_dev implementation report output.

Usage:
    python validate.py <implementation_report.yaml>
    python validate.py --stdin < implementation_report.yaml

Returns:
    0 if valid, 1 if invalid with error messages on stderr
"""

import sys
from pathlib import Path
from typing import Any

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


VALID_TEST_STATUS = {"PASSED", "STILL_FAILING"}
VALID_CHANGE_ACTIONS = {"created", "modified", "deleted"}


def validate_meta(meta: dict[str, Any]) -> list[str]:
    """Validate meta section."""
    errors = []

    if "ticket_id" not in meta:
        errors.append("meta.ticket_id is required")

    if meta.get("implementer") != "senior_dev":
        errors.append("meta.implementer must be 'senior_dev'")

    tdd_cycle = meta.get("tdd_cycle")
    if tdd_cycle is None:
        errors.append("meta.tdd_cycle is required")
    elif not isinstance(tdd_cycle, int) or tdd_cycle < 1:
        errors.append("meta.tdd_cycle must be a positive integer")

    return errors


def validate_tests_addressed(tests: list[dict[str, Any]] | None) -> list[str]:
    """Validate tests_addressed section."""
    if not tests:
        return ["At least one test must be addressed"]

    errors = []
    for i, test in enumerate(tests):
        prefix = f"tests_addressed[{i}]"

        if "test_file" not in test:
            errors.append(f"{prefix}.test_file is required")

        if "test_name" not in test:
            errors.append(f"{prefix}.test_name is required")

        status = test.get("status")
        if status not in VALID_TEST_STATUS:
            errors.append(f"{prefix}.status must be one of {VALID_TEST_STATUS}")

    return errors


def validate_changes(changes: list[dict[str, Any]] | None) -> list[str]:
    """Validate changes section."""
    if not changes:
        return ["At least one change must be reported"]

    errors = []
    for i, change in enumerate(changes):
        prefix = f"changes[{i}]"

        if "file" not in change:
            errors.append(f"{prefix}.file is required")

        action = change.get("action")
        if action not in VALID_CHANGE_ACTIONS:
            errors.append(f"{prefix}.action must be one of {VALID_CHANGE_ACTIONS}")

        if "summary" not in change:
            errors.append(f"{prefix}.summary is required")

    return errors


def validate_verification(verification: dict[str, Any] | None) -> list[str]:
    """Validate verification section."""
    if verification is None:
        return ["verification section is required"]

    errors = []

    for field in ["tests_run", "tests_passing", "linter_run", "linter_clean"]:
        if field not in verification:
            errors.append(f"verification.{field} is required")
        elif not isinstance(verification[field], bool):
            errors.append(f"verification.{field} must be a boolean")

    # Warn if tests not passing or linter not clean
    if verification.get("tests_passing") is False:
        print("Warning: Tests are not passing", file=sys.stderr)

    if verification.get("linter_clean") is False:
        print("Warning: Linter issues remain", file=sys.stderr)

    return errors


def validate_confidence(confidence: dict[str, Any] | None) -> list[str]:
    """Validate confidence section."""
    if confidence is None:
        return ["confidence section is required"]

    errors = []

    score = confidence.get("score")
    if score is None:
        errors.append("confidence.score is required")
    elif not isinstance(score, (int, float)) or not 0 <= score <= 1:
        errors.append("confidence.score must be a number between 0 and 1")

    if "rationale" not in confidence:
        errors.append("confidence.rationale is required")

    return errors


def validate_report(spec: dict[str, Any]) -> list[str]:
    """Validate a complete implementation report."""
    errors = []

    if "meta" not in spec:
        errors.append("meta section is required")
    else:
        errors.extend(validate_meta(spec["meta"]))

    errors.extend(validate_tests_addressed(spec.get("tests_addressed")))
    errors.extend(validate_changes(spec.get("changes")))
    errors.extend(validate_verification(spec.get("verification")))
    errors.extend(validate_confidence(spec.get("confidence")))

    return errors


def main() -> int:
    """Main entry point."""
    if not HAS_YAML:
        print("Error: PyYAML is required for validation", file=sys.stderr)
        print("Install with: pip install pyyaml", file=sys.stderr)
        return 1

    if len(sys.argv) < 2:
        print("Usage: validate.py <implementation_report.yaml>", file=sys.stderr)
        print("       validate.py --stdin < report.yaml", file=sys.stderr)
        return 1

    if sys.argv[1] == "--stdin":
        content = sys.stdin.read()
    else:
        path = Path(sys.argv[1])
        if not path.exists():
            print(f"Error: File not found: {path}", file=sys.stderr)
            return 1
        content = path.read_text()

    try:
        spec = yaml.safe_load(content)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML: {e}", file=sys.stderr)
        return 1

    if not isinstance(spec, dict):
        print("Error: Report must be a YAML mapping", file=sys.stderr)
        return 1

    errors = validate_report(spec)

    if errors:
        print(f"Validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Validation passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
