## ASSUMPTION LOGGING - STATE BEFORE ACTING

Before taking action, you MUST explicitly document your assumptions:

```yaml
ASSUMPTIONS:
  - assumption: <what you're assuming>
    source: stated|inferred|prior_knowledge|undocumented
    risk: LOW|MEDIUM|HIGH
    validation: <how this could be verified>
```

Risk levels:
- **HIGH**: Assumption could invalidate work if wrong -> MUST trigger spike
- **MEDIUM**: Assumption affects details -> Note for review
- **LOW**: Assumption is likely correct, easy to change later

Examples:
- "Database supports transactions" (source: inferred, risk: HIGH)
- "Using existing auth middleware" (source: stated in ticket, risk: LOW)
- "p99 latency target is 100ms" (source: undocumented, risk: HIGH -> SPIKE)

NEVER proceed with HIGH-risk undocumented assumptions. Request a spike instead.
