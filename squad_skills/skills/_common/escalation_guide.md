## WHEN TO ESCALATE

**Stop and request clarification when:**

- Requirements are ambiguous or contradictory
- Multiple valid approaches exist with different tradeoffs
- Security implications are unclear
- You're blocked for >15 minutes with no progress
- The task requires work outside your role
- You discover issues that affect other tickets

**How to escalate:**

In your output, include an `## Escalation` section:

```yaml
## Escalation

status: BLOCKED | NEEDS_DECISION | INFO_ONLY
reason: <brief description>
options:
  - option: <approach A>
    tradeoffs: <pros/cons>
  - option: <approach B>
    tradeoffs: <pros/cons>
recommendation: <which option and why>
```

**It's better to ask than to guess wrong.**
