#!/usr/bin/env python3
"""Validate architect design specification output.

This script validates that an architect's output conforms to the
design_spec.yaml template structure and contains all required sections.

Usage:
    python validate.py <design_spec.yaml>
    python validate.py --stdin < design_spec.yaml

Returns:
    0 if valid, 1 if invalid with error messages on stderr
"""

import sys
from pathlib import Path
from typing import Any

# Try to use PyYAML if available, otherwise basic validation only
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# Required top-level sections
REQUIRED_SECTIONS = [
    "meta",
    "assumptions",
    "overview",
    "interfaces",
    "data_flow",
    "error_handling",
    "threat_model",
    "nfr",
    "observability",
    "eval_criteria",
    "confidence",
]

# Sections that can be null for greenfield projects
OPTIONAL_SECTIONS = ["system_context", "open_questions"]

# Valid enum values
VALID_ASSUMPTION_SOURCES = {"stated", "inferred", "undocumented"}
VALID_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}
VALID_STRIDE_CATEGORIES = {"S", "T", "R", "I", "D", "E"}
VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_METRIC_TYPES = {"counter", "gauge", "histogram"}
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARN", "ERROR"}
VALID_ALERT_SEVERITIES = {"page", "ticket", "log"}
VALID_INTERFACE_TYPES = {"protocol", "abstract_class", "interface"}


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_meta(meta: dict[str, Any]) -> list[str]:
    """Validate meta section."""
    errors = []
    required_fields = ["ticket_id", "author", "version"]

    for field in required_fields:
        if field not in meta:
            errors.append(f"meta.{field} is required")

    if meta.get("author") != "architect":
        errors.append("meta.author must be 'architect'")

    return errors


def validate_assumptions(assumptions: list[dict[str, Any]]) -> list[str]:
    """Validate assumptions section."""
    errors = []

    if not assumptions:
        errors.append("At least one assumption is required")
        return errors

    for i, assumption in enumerate(assumptions):
        prefix = f"assumptions[{i}]"

        if "assumption" not in assumption:
            errors.append(f"{prefix}.assumption is required")

        source = assumption.get("source")
        if source not in VALID_ASSUMPTION_SOURCES:
            errors.append(f"{prefix}.source must be one of {VALID_ASSUMPTION_SOURCES}")

        risk = assumption.get("risk")
        if risk not in VALID_RISK_LEVELS:
            errors.append(f"{prefix}.risk must be one of {VALID_RISK_LEVELS}")

        if "validation" not in assumption:
            errors.append(f"{prefix}.validation is required")

    return errors


def validate_threat_model(threats: list[dict[str, Any]]) -> list[str]:
    """Validate STRIDE threat model section."""
    errors = []

    if not threats:
        errors.append("threat_model must contain at least one threat")
        return errors

    categories_covered = set()

    for i, threat in enumerate(threats):
        prefix = f"threat_model[{i}]"

        if "threat" not in threat:
            errors.append(f"{prefix}.threat description is required")

        category = threat.get("category")
        if category not in VALID_STRIDE_CATEGORIES:
            errors.append(f"{prefix}.category must be one of {VALID_STRIDE_CATEGORIES}")
        else:
            categories_covered.add(category)

        severity = threat.get("severity")
        if severity not in VALID_SEVERITIES:
            errors.append(f"{prefix}.severity must be one of {VALID_SEVERITIES}")

        if "mitigation" not in threat:
            errors.append(f"{prefix}.mitigation is required")

    # Warn if not all STRIDE categories are covered
    missing = VALID_STRIDE_CATEGORIES - categories_covered
    if missing:
        # This is a warning, not an error
        print(f"Warning: STRIDE categories not covered: {missing}", file=sys.stderr)

    return errors


def validate_nfr(nfr: dict[str, Any]) -> list[str]:
    """Validate non-functional requirements section."""
    errors = []

    required_subsections = ["reliability", "performance", "scalability"]
    for subsection in required_subsections:
        if subsection not in nfr:
            errors.append(f"nfr.{subsection} is required")

    # Validate performance has measurable targets
    perf = nfr.get("performance", {})
    for latency in ["p50_latency_ms", "p95_latency_ms", "p99_latency_ms"]:
        if latency not in perf:
            errors.append(f"nfr.performance.{latency} is required")
        elif not isinstance(perf[latency], (int, float)):
            errors.append(f"nfr.performance.{latency} must be a number")

    return errors


def validate_interfaces(interfaces: list[dict[str, Any]]) -> list[str]:
    """Validate interfaces section."""
    errors = []

    if not interfaces:
        errors.append("At least one interface definition is required")
        return errors

    for i, interface in enumerate(interfaces):
        prefix = f"interfaces[{i}]"

        if "name" not in interface:
            errors.append(f"{prefix}.name is required")

        itype = interface.get("type")
        if itype not in VALID_INTERFACE_TYPES:
            errors.append(f"{prefix}.type must be one of {VALID_INTERFACE_TYPES}")

        if "definition" not in interface:
            errors.append(f"{prefix}.definition is required")

    return errors


def validate_observability(obs: dict[str, Any]) -> list[str]:
    """Validate observability section."""
    errors = []

    required_subsections = ["metrics", "logging", "tracing", "alerts"]
    for subsection in required_subsections:
        if subsection not in obs:
            errors.append(f"observability.{subsection} is required")

    # Validate metrics
    for i, metric in enumerate(obs.get("metrics", [])):
        prefix = f"observability.metrics[{i}]"
        mtype = metric.get("type")
        if mtype not in VALID_METRIC_TYPES:
            errors.append(f"{prefix}.type must be one of {VALID_METRIC_TYPES}")

    # Validate logging
    for i, log in enumerate(obs.get("logging", [])):
        prefix = f"observability.logging[{i}]"
        level = log.get("level")
        if level not in VALID_LOG_LEVELS:
            errors.append(f"{prefix}.level must be one of {VALID_LOG_LEVELS}")

    return errors


def validate_confidence(confidence: dict[str, Any]) -> list[str]:
    """Validate confidence section."""
    errors = []

    overall = confidence.get("overall")
    if overall is None:
        errors.append("confidence.overall is required")
    elif not isinstance(overall, (int, float)) or not 0 <= overall <= 1:
        errors.append("confidence.overall must be a number between 0 and 1")

    areas = confidence.get("areas", [])
    if not areas:
        errors.append("confidence.areas must have at least one entry")

    for i, area in enumerate(areas):
        prefix = f"confidence.areas[{i}]"
        conf = area.get("confidence")
        if conf is None:
            errors.append(f"{prefix}.confidence is required")
        elif not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
            errors.append(f"{prefix}.confidence must be between 0 and 1")

        if "reasoning" not in area:
            errors.append(f"{prefix}.reasoning is required")

    return errors


def validate_design_spec(spec: dict[str, Any]) -> list[str]:
    """Validate a complete design specification."""
    errors = []

    # Check required sections
    for section in REQUIRED_SECTIONS:
        if section not in spec:
            errors.append(f"Missing required section: {section}")

    # Validate each section
    if "meta" in spec:
        errors.extend(validate_meta(spec["meta"]))

    if "assumptions" in spec:
        errors.extend(validate_assumptions(spec["assumptions"]))

    if "threat_model" in spec:
        errors.extend(validate_threat_model(spec["threat_model"]))

    if "nfr" in spec:
        errors.extend(validate_nfr(spec["nfr"]))

    if "interfaces" in spec:
        errors.extend(validate_interfaces(spec["interfaces"]))

    if "observability" in spec:
        errors.extend(validate_observability(spec["observability"]))

    if "confidence" in spec:
        errors.extend(validate_confidence(spec["confidence"]))

    return errors


def main() -> int:
    """Main entry point."""
    if not HAS_YAML:
        print("Error: PyYAML is required for validation", file=sys.stderr)
        print("Install with: pip install pyyaml", file=sys.stderr)
        return 1

    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: validate.py <design_spec.yaml>", file=sys.stderr)
        print("       validate.py --stdin < design_spec.yaml", file=sys.stderr)
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
        print("Error: Design spec must be a YAML mapping", file=sys.stderr)
        return 1

    # Validate
    errors = validate_design_spec(spec)

    if errors:
        print(f"Validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Validation passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
