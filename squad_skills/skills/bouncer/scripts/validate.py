#!/usr/bin/env python3
"""Validate bouncer review decision output.

This script validates that a bouncer's review output conforms to the
review.yaml template structure and contains all required sections.

Usage:
    python validate.py <review.yaml>
    python validate.py --stdin < review.yaml

Returns:
    0 if valid, 1 if invalid with error messages on stderr
"""

import sys
from pathlib import Path
from typing import Any

# Try to use PyYAML if available
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# Valid enum values
VALID_GATES = {"gate_1", "gate_2", "gate_3"}
VALID_DECISIONS = {"APPROVED", "REJECTED"}
VALID_PASS_FAIL = {"PASS", "FAIL", "NA"}
VALID_PASS_FAIL_WARNING = {"PASS", "FAIL", "WARNING"}
VALID_SEVERITIES = {"blocker", "must_fix", "should_fix"}


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_meta(meta: dict[str, Any]) -> list[str]:
    """Validate meta section."""
    errors = []

    if "ticket_id" not in meta:
        errors.append("meta.ticket_id is required")

    gate = meta.get("gate")
    if gate not in VALID_GATES:
        errors.append(f"meta.gate must be one of {VALID_GATES}")

    if meta.get("reviewer") != "bouncer":
        errors.append("meta.reviewer must be 'bouncer'")

    return errors


def validate_gate_1(review: dict[str, Any] | None) -> list[str]:
    """Validate Gate 1 (Design Review) section."""
    if review is None:
        return []

    errors = []
    required_checks = [
        "acceptance_criteria_coverage",
        "interfaces_clarity",
        "error_handling_considered",
        "scope_appropriate",
        "tdd_testable",
        "nfr_specified",
        "observability_defined",
        "eval_criteria_measurable",
        "stride_complete",
    ]

    for check in required_checks:
        value = review.get(check)
        if value not in VALID_PASS_FAIL:
            errors.append(f"design_review.{check} must be one of {VALID_PASS_FAIL}")

    return errors


def validate_architectural_drift(drift: dict[str, Any] | None) -> list[str]:
    """Validate architectural drift checks."""
    if drift is None:
        return ["code_review.architectural_drift is required for Gate 2"]

    errors = []
    checks = [
        "circular_dependencies",
        "layer_violations",
        "god_objects",
        "pattern_consistency",
        "complexity_budget",
    ]

    for check in checks:
        value = drift.get(check)
        if value not in VALID_PASS_FAIL_WARNING:
            errors.append(f"architectural_drift.{check} must be one of {VALID_PASS_FAIL_WARNING}")

    return errors


def validate_dead_code(dead_code: dict[str, Any] | None) -> list[str]:
    """Validate dead code detection section."""
    if dead_code is None:
        return ["code_review.dead_code is required for Gate 2"]

    errors = []

    for check in ["unused_imports", "unused_functions"]:
        value = dead_code.get(check)
        if value not in VALID_PASS_FAIL_WARNING:
            errors.append(f"dead_code.{check} must be one of {VALID_PASS_FAIL_WARNING}")

    for check in ["unreachable_code", "commented_code"]:
        value = dead_code.get(check)
        if value not in {"PASS", "FAIL"}:
            errors.append(f"dead_code.{check} must be PASS or FAIL")

    return errors


def validate_security(security: dict[str, Any] | None) -> list[str]:
    """Validate security checklist."""
    if security is None:
        return ["code_review.security is required for Gate 2"]

    errors = []
    checks = [
        "hardcoded_secrets",
        "input_validation",
        "sql_injection",
        "xss",
        "auth_checks",
        "dependencies",
        "sensitive_logging",
    ]

    for check in checks:
        value = security.get(check)
        if value not in {"PASS", "FAIL"}:
            errors.append(f"security.{check} must be PASS or FAIL")

    return errors


def validate_gate_2(review: dict[str, Any] | None) -> list[str]:
    """Validate Gate 2 (Code Review) section."""
    if review is None:
        return []

    errors = []

    # Basic checks
    basic_checks = [
        "implementation_matches_design",
        "tests_passing",
        "code_style",
        "error_handling",
    ]
    for check in basic_checks:
        value = review.get(check)
        if value not in VALID_PASS_FAIL:
            errors.append(f"code_review.{check} must be one of {VALID_PASS_FAIL}")

    # Sub-sections
    errors.extend(validate_architectural_drift(review.get("architectural_drift")))
    errors.extend(validate_dead_code(review.get("dead_code")))
    errors.extend(validate_security(review.get("security")))

    return errors


def validate_gate_3(review: dict[str, Any] | None) -> list[str]:
    """Validate Gate 3 (Pre-Production) section."""
    if review is None:
        return []

    errors = []
    checks = [
        "all_tests_passing",
        "performance_meets_nfr",
        "observability_implemented",
        "documentation_complete",
        "runbooks_created",
    ]

    for check in checks:
        value = review.get(check)
        if value not in VALID_PASS_FAIL:
            errors.append(f"preprod_review.{check} must be one of {VALID_PASS_FAIL}")

    return errors


def validate_feedback(feedback: dict[str, Any] | None) -> list[str]:
    """Validate feedback section."""
    if feedback is None:
        return ["feedback section is required"]

    errors = []

    if "summary" not in feedback:
        errors.append("feedback.summary is required")

    return errors


def validate_action_items(items: list[dict[str, Any]] | None, decision: str) -> list[str]:
    """Validate action items section."""
    errors = []

    if decision == "REJECTED" and (not items or len(items) == 0):
        errors.append("action_items are required when decision is REJECTED")

    if items:
        for i, item in enumerate(items):
            if "description" not in item:
                errors.append(f"action_items[{i}].description is required")

            severity = item.get("severity")
            if severity and severity not in VALID_SEVERITIES:
                errors.append(f"action_items[{i}].severity must be one of {VALID_SEVERITIES}")

    return errors


def validate_confidence(confidence: dict[str, Any] | None) -> list[str]:
    """Validate confidence section."""
    if confidence is None:
        return ["confidence section is required"]

    errors = []

    score = confidence.get("score")
    if score is None:
        errors.append("confidence.score is required")
    elif not isinstance(score, (int, float)) or not 0 <= score <= 100:
        errors.append("confidence.score must be a number between 0 and 100")

    if "rationale" not in confidence:
        errors.append("confidence.rationale is required")

    return errors


def validate_review(spec: dict[str, Any]) -> list[str]:
    """Validate a complete review output."""
    errors = []

    # Check meta
    if "meta" not in spec:
        errors.append("meta section is required")
        return errors  # Can't continue without meta

    errors.extend(validate_meta(spec["meta"]))
    gate = spec["meta"].get("gate")

    # Check decision
    decision = spec.get("decision")
    if decision not in VALID_DECISIONS:
        errors.append(f"decision must be one of {VALID_DECISIONS}")

    # Validate gate-specific sections
    if gate == "gate_1":
        if spec.get("design_review") is None:
            errors.append("design_review is required for Gate 1")
        else:
            errors.extend(validate_gate_1(spec.get("design_review")))

    elif gate == "gate_2":
        if spec.get("code_review") is None:
            errors.append("code_review is required for Gate 2")
        else:
            errors.extend(validate_gate_2(spec.get("code_review")))

    elif gate == "gate_3":
        if spec.get("preprod_review") is None:
            errors.append("preprod_review is required for Gate 3")
        else:
            errors.extend(validate_gate_3(spec.get("preprod_review")))

    # Validate common sections
    errors.extend(validate_feedback(spec.get("feedback")))
    errors.extend(validate_action_items(spec.get("action_items"), decision or ""))
    errors.extend(validate_confidence(spec.get("confidence")))

    return errors


def main() -> int:
    """Main entry point."""
    if not HAS_YAML:
        print("Error: PyYAML is required for validation", file=sys.stderr)
        print("Install with: pip install pyyaml", file=sys.stderr)
        return 1

    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: validate.py <review.yaml>", file=sys.stderr)
        print("       validate.py --stdin < review.yaml", file=sys.stderr)
        return 1

    # Read input
    if sys.argv[1] == "--stdin":
        content = sys.stdin.read()
    else:
        path = Path(sys.argv[1])
        if not path.exists():
            print(f"Error: File not found: {path}", file=sys.stderr)
            return 1
        content = path.read_text()

    # Parse YAML
    try:
        spec = yaml.safe_load(content)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML: {e}", file=sys.stderr)
        return 1

    if not isinstance(spec, dict):
        print("Error: Review must be a YAML mapping", file=sys.stderr)
        return 1

    # Validate
    errors = validate_review(spec)

    if errors:
        print(f"Validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Validation passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
