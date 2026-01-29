#!/usr/bin/env python3
"""Validate product_owner output (clarification or ticket).

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


VALID_TICKET_TYPES = {"feature", "bug", "spike", "tech_debt"}
VALID_STORY_POINTS = {1, 2, 3, 5, 8, 13}
VALID_RISKS = {"LOW", "MEDIUM", "HIGH"}
VALID_SOURCES = {"mission_doc", "inferred", "industry_standard", "clarified"}
VALID_CLARIFICATION_STATUS = {"NEEDS_CLARIFICATION", "READY_TO_DECOMPOSE"}
VALID_MISSING_CATEGORIES = {"users", "scale", "constraints", "success_criteria", "timeline"}


def validate_clarification(spec: dict[str, Any]) -> list[str]:
    """Validate a clarification request."""
    errors = []

    if "original_mission" not in spec:
        errors.append("original_mission is required")

    if "interpretation" not in spec:
        errors.append("interpretation is required")
    else:
        interp = spec["interpretation"]
        if "summary" not in interp:
            errors.append("interpretation.summary is required")
        conf = interp.get("confidence")
        if conf is not None and not (0 <= conf <= 1):
            errors.append("interpretation.confidence must be between 0 and 1")

    if "questions" not in spec or len(spec.get("questions", [])) == 0:
        errors.append("At least one clarifying question is required")

    questions = spec.get("questions", [])
    for i, q in enumerate(questions):
        if "question" not in q:
            errors.append(f"questions[{i}].question is required")
        if "priority" not in q:
            errors.append(f"questions[{i}].priority is required")

    status = spec.get("status")
    if status not in VALID_CLARIFICATION_STATUS:
        errors.append(f"status must be one of {VALID_CLARIFICATION_STATUS}")

    return errors


def validate_ticket(spec: dict[str, Any]) -> list[str]:
    """Validate a ticket."""
    errors = []

    # Required fields
    if "title" not in spec:
        errors.append("title is required")

    ticket_type = spec.get("type")
    if ticket_type not in VALID_TICKET_TYPES:
        errors.append(f"type must be one of {VALID_TICKET_TYPES}")

    story_points = spec.get("story_points")
    if story_points not in VALID_STORY_POINTS:
        errors.append(f"story_points must be one of {VALID_STORY_POINTS}")

    # Acceptance criteria (required for non-spike tickets)
    if ticket_type != "spike":
        criteria = spec.get("acceptance_criteria", [])
        if len(criteria) == 0:
            errors.append("At least one acceptance criterion is required")

        for i, criterion in enumerate(criteria):
            prefix = f"acceptance_criteria[{i}]"

            if "criterion" not in criterion:
                errors.append(f"{prefix}.criterion is required")

            # Eval is required
            eval_spec = criterion.get("eval")
            if eval_spec is None:
                errors.append(f"{prefix}.eval is required")
            else:
                if "script" not in eval_spec:
                    errors.append(f"{prefix}.eval.script is required")
                if "metric" not in eval_spec:
                    errors.append(f"{prefix}.eval.metric is required")

                # Check metric is quantifiable (not vague words)
                metric = eval_spec.get("metric", "")
                vague_words = ["fast", "quick", "good", "nice", "easy", "simple", "better"]
                for word in vague_words:
                    if word in metric.lower() and not any(c.isdigit() for c in metric):
                        errors.append(
                            f"{prefix}.eval.metric contains vague word '{word}' - "
                            "use quantifiable thresholds"
                        )

    # NFR validation (required for feature tickets)
    if ticket_type == "feature":
        nfr = spec.get("nfr")
        if nfr is None:
            errors.append("nfr section is required for feature tickets")
        else:
            # Latency
            latency = nfr.get("latency", {})
            for field in ["p50_ms", "p95_ms", "p99_ms"]:
                if field not in latency:
                    errors.append(f"nfr.latency.{field} is required")
                elif not isinstance(latency[field], (int, float)):
                    errors.append(f"nfr.latency.{field} must be a number")

            # Reliability
            reliability = nfr.get("reliability", {})
            if "availability_sla" not in reliability:
                errors.append("nfr.reliability.availability_sla is required")

    # Confidence
    confidence = spec.get("confidence")
    if confidence is None:
        errors.append("confidence section is required")
    else:
        score = confidence.get("score")
        if score is None:
            errors.append("confidence.score is required")
        elif not isinstance(score, (int, float)) or not 0 <= score <= 100:
            errors.append("confidence.score must be between 0 and 100")

    return errors


def detect_and_validate(spec: dict[str, Any]) -> list[str]:
    """Detect document type and validate accordingly."""
    # Detect type based on content
    if "original_mission" in spec or "questions" in spec:
        return validate_clarification(spec)
    elif "title" in spec or "acceptance_criteria" in spec:
        return validate_ticket(spec)
    else:
        return ["Cannot determine document type - must be clarification or ticket"]


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
