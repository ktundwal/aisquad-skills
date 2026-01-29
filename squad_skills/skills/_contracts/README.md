# Agent Handoff Contracts

This directory defines the data contracts between agents in the Squad workflow.
Contracts ensure agents can communicate reliably in autonomous mode.

## Workflow Overview

```
┌─────────────────┐
│    [HUMAN]      │ ─── provides ──→ Vague Mission
└────────┬────────┘
         │
         ↓ mission
┌─────────────────┐
│  product_owner  │ ─── produces ──→ Clarification questions OR Tickets
└────────┬────────┘
         │
         ↓ ticket.yaml (with clear acceptance criteria)
┌─────────────────┐
│    architect    │ ─── produces ──→ DesignSpec (interfaces, NFRs, STRIDE)
└────────┬────────┘
         │
         ↓ design_spec.yaml
┌─────────────────┐
│     bouncer     │ ─── produces ──→ ReviewDecision (Gate 1: design review)
│    (Gate 1)     │
└────────┬────────┘
         │
         ↓ APPROVED
┌─────────────────┐
│       dev       │ ─── produces ──→ FailingTests (TDD red phase)
│   (Junior)      │
└────────┬────────┘
         │
         ↓ test files
┌─────────────────┐
│   senior_dev    │ ─── produces ──→ ImplementationReport (TDD green phase)
└────────┬────────┘
         │
         ↓ implementation_report.yaml
┌─────────────────┐
│     bouncer     │ ─── produces ──→ ReviewDecision (Gate 2: code review)
│    (Gate 2)     │
└────────┬────────┘
         │
         ↓ APPROVED
┌─────────────────┐
│   qa_engineer   │ ─── produces ──→ QAReport (integration tests, e2e)
└────────┬────────┘
         │
         ↓ qa_report.yaml
┌─────────────────┐
│     on_call     │ ─── produces ──→ OperationalReadiness (5-25 rule check)
└────────┬────────┘
         │
         ↓ operational_readiness.yaml
┌─────────────────┐
│     bouncer     │ ─── produces ──→ ReviewDecision (Gate 3: pre-prod)
│    (Gate 3)     │
└────────┬────────┘
         │
         ↓ APPROVED → DONE (code is now a supported liability)
```

## Contract Files

| Contract | Producer | Consumer | Description |
|----------|----------|----------|-------------|
| `clarification.yaml` | product_owner | human | Questions to clarify vague missions |
| `ticket.yaml` | product_owner | architect, manager | Work item with acceptance criteria |
| `design_spec.yaml` | architect | bouncer, senior_dev | Technical design specification |
| `review_decision.yaml` | bouncer | manager | Approval/rejection decision |
| `implementation_report.yaml` | senior_dev | bouncer, qa_engineer | What was implemented |
| `qa_report.yaml` | qa_engineer | on_call | Test results and coverage |
| `operational_readiness.yaml` | on_call | bouncer | 5-25 rule verification |

## Using Contracts

Agents should:
1. Validate incoming data against the contract schema
2. Produce output that conforms to the contract schema
3. Reject malformed input with clear error messages

Example validation:
```python
from squad_skills import load_skill_with_metadata

skill = load_skill_with_metadata("architect")
validate_script = skill.resources.scripts.get("validate")

if validate_script:
    import subprocess
    result = subprocess.run(
        ["python", str(validate_script), "output.yaml"],
        capture_output=True
    )
    if result.returncode != 0:
        raise ValueError(f"Invalid output: {result.stderr}")
```

## Contract Versioning

Contracts use semantic versioning:
- **Major**: Breaking changes (new required fields, removed fields)
- **Minor**: Backwards-compatible additions (new optional fields)
- **Patch**: Documentation/description changes

Current versions:
- `ticket.yaml`: 1.0.0
- `design_spec.yaml`: 1.0.0
- `review_decision.yaml`: 1.0.0
- `implementation_report.yaml`: 1.0.0
- `qa_report.yaml`: 1.0.0
