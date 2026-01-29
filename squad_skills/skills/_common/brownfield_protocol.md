## BROWNFIELD PROTOCOL - RESPECT THE CODEBASE

When working in existing codebases:

1. **RESPECT THE LINTER**: Run linting before and after changes
   - Fix any lint errors you introduce
   - Match the project's lint configuration
   - Format code according to project settings

2. **FOLLOW EXISTING PATTERNS**: Before writing new code, search for similar patterns
   - Variable naming conventions
   - Module/class organization
   - Error handling approaches
   - Logging and observability patterns
   - Test organization and naming

3. **BOY SCOUT RULE**: Leave code CLEANER than you found it
   - Fix small issues in files you touch (typos, unused imports)
   - Improve unclear variable names in your vicinity
   - Add missing type hints to functions you modify
   - DO NOT refactor unrelated code - stay focused on the ticket
