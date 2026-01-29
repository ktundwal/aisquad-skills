## CONFIDENCE SCORING - MANAGE CONFUSION

Your output MUST include a confidence score:

```yaml
CONFIDENCE: <0-100>%
RATIONALE: <why this confidence level>
```

Thresholds:
- **HIGH (80-100%)**: Proceed normally
- **MEDIUM (50-79%)**: Flag for human review, may proceed with caution
- **LOW (0-49%)**: AUTO-SPIKE - Do NOT proceed, create spike ticket

If confidence < 50%, add: `SPIKE_NEEDED: <what would raise confidence>`

Low confidence situations:
- Requirements are ambiguous
- Multiple valid interpretations exist
- Missing information affects correctness
- Unsure if approach matches intent
