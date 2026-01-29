#!/usr/bin/env python3
"""Validate on_call output (operational readiness or incident report).

Usage:
    python validate.py <output.yaml>
    python validate.py --stdin < output.yaml

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


VALID_DEPLOYMENT_TYPES = {"service", "application", "cli", "library"}
VALID_5_25_STATUS = {"MEETS", "AT_RISK", "FAILS"}
VALID_OBSERVABILITY_STATUS = {"COMPLETE", "PARTIAL", "MISSING"}
VALID_DECISIONS = {"APPROVED", "CONDITIONAL", "REJECTED"}
VALID_SEVERITIES = {"P1", "P2", "P3", "P4"}
VALID_INCIDENT_STATUS = {"INVESTIGATING", "MITIGATING", "RESOLVED", "POSTMORTEM"}


def validate_five_twenty_five(spec: dict[str, Any]) -> list[str]:
    """Validate the 5-25 rule assessment."""
    errors = []

    if "five_twenty_five" not in spec:
        errors.append("five_twenty_five assessment is required")
        return errors

    ftf = spec["five_twenty_five"]

    for target in ["time_to_detect", "time_to_resolve"]:
        if target not in ftf:
            errors.append(f"five_twenty_five.{target} is required")
            continue

        t = ftf[target]
        if "estimated_minutes" not in t:
            errors.append(f"five_twenty_five.{target}.estimated_minutes is required")

        status = t.get("status")
        if status not in VALID_5_25_STATUS:
            errors.append(f"five_twenty_five.{target}.status must be one of {VALID_5_25_STATUS}")

        # Warn if FAILS
        if status == "FAILS":
            print(f"Warning: {target} FAILS the 5-25 rule", file=sys.stderr)

    return errors


def validate_observability(spec: dict[str, Any]) -> list[str]:
    """Validate observability checklist."""
    errors = []

    obs = spec.get("observability")
    if obs is None:
        errors.append("observability section is required")
        return errors

    for section in ["metrics", "logging", "alerting"]:
        if section not in obs:
            errors.append(f"observability.{section} is required")
            continue

        status = obs[section].get("status")
        if status not in VALID_OBSERVABILITY_STATUS:
            errors.append(
                f"observability.{section}.status must be one of {VALID_OBSERVABILITY_STATUS}"
            )

    # Check alerts have runbooks
    alerts = obs.get("alerting", {}).get("alerts", [])
    for i, alert in enumerate(alerts):
        severity = alert.get("severity")
        runbook = alert.get("runbook")
        if severity in ["critical", "warning"] and not runbook:
            errors.append(f"observability.alerting.alerts[{i}]: {severity} alert requires runbook")

    return errors


def validate_operational_readiness(spec: dict[str, Any]) -> list[str]:
    """Validate operational readiness review."""
    errors = []

    # Meta
    if "meta" not in spec:
        errors.append("meta section is required")
    else:
        deploy_type = spec["meta"].get("deployment_type")
        if deploy_type not in VALID_DEPLOYMENT_TYPES:
            errors.append(f"meta.deployment_type must be one of {VALID_DEPLOYMENT_TYPES}")

    # 5-25 Rule
    errors.extend(validate_five_twenty_five(spec))

    # Observability
    errors.extend(validate_observability(spec))

    # Decision
    decision = spec.get("decision")
    if decision not in VALID_DECISIONS:
        errors.append(f"decision must be one of {VALID_DECISIONS}")

    # Conditional must have conditions
    if decision == "CONDITIONAL":
        conditions = spec.get("conditions", [])
        if len(conditions) == 0:
            errors.append("CONDITIONAL decision requires at least one condition")

    # Rejected must have blockers
    if decision == "REJECTED":
        blockers = spec.get("blockers", [])
        if len(blockers) == 0:
            errors.append("REJECTED decision requires at least one blocker")

    # Confidence
    confidence = spec.get("confidence")
    if confidence is None:
        errors.append("confidence section is required")
    else:
        score = confidence.get("score")
        if score is None or not isinstance(score, (int, float)) or not 0 <= score <= 100:
            errors.append("confidence.score must be between 0 and 100")

    return errors


def validate_incident(spec: dict[str, Any]) -> list[str]:
    """Validate incident report."""
    errors = []

    # Status
    status = spec.get("status")
    if status not in VALID_INCIDENT_STATUS:
        errors.append(f"status must be one of {VALID_INCIDENT_STATUS}")

    # Severity
    severity = spec.get("severity", {})
    level = severity.get("level")
    if level not in VALID_SEVERITIES:
        errors.append(f"severity.level must be one of {VALID_SEVERITIES}")

    # Summary
    if "summary" not in spec:
        errors.append("summary section is required")
    else:
        if "title" not in spec["summary"]:
            errors.append("summary.title is required")

    # Timeline
    timeline = spec.get("timeline", [])
    if len(timeline) == 0:
        errors.append("At least one timeline entry is required")

    # Detection
    detection = spec.get("detection")
    if detection:
        ttd = detection.get("time_to_detect_minutes")
        if ttd is not None and ttd > 5:
            print(f"Warning: Time to detect ({ttd} min) exceeds 5-minute target", file=sys.stderr)

    # Resolution (if resolved)
    if status in ["RESOLVED", "POSTMORTEM"]:
        resolution = spec.get("resolution", {})
        ttr = resolution.get("time_to_resolve_minutes")
        if ttr is not None and ttr > 25:
            print(f"Warning: Time to resolve ({ttr} min) exceeds 25-minute target", file=sys.stderr)

    return errors


def detect_and_validate(spec: dict[str, Any]) -> list[str]:
    """Detect document type and validate accordingly."""
    # Detect type
    if "five_twenty_five" in spec or "observability" in spec:
        return validate_operational_readiness(spec)
    elif "incident_id" in spec.get("meta", {}) or "severity" in spec:
        return validate_incident(spec)
    else:
        return ["Cannot determine document type - must be operational_readiness or incident"]


def main() -> int:
    """Main entry point."""
    if not HAS_YAML:
        print("Error: PyYAML is required for validation", file=sys.stderr)
        return 1

    if len(sys.argv) < 2:
        print("Usage: validate.py <output.yaml>", file=sys.stderr)
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
        print("Error: Output must be a YAML mapping", file=sys.stderr)
        return 1

    errors = detect_and_validate(spec)

    if errors:
        print(f"Validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Validation passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
