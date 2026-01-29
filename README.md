# Squad Skills

Battle-tested agent prompts for AI development teams.

## Overview

Squad Skills provides reusable, composable prompt templates for AI agents that follow:
- **TDD methodology** (Red → Green → Refactor)
- **Spike protocols** (investigate before committing)
- **Assumption logging** (document what you don't know)
- **Confidence scoring** (quantify uncertainty)
- **Brownfield best practices** (respect existing code)

These skills are extracted from the [Squad](https://github.com/ai-dev-team/squad) orchestrator but can be used independently with any LLM orchestration framework.

Compatible with the [Agent Skills](https://agentskills.io) open standard.

## Installation

```bash
pip install squad-skills
```

Or with uv:

```bash
uv add squad-skills
```

## Quick Start

```python
from squad_skills import load_skill, list_skills

# Load a specific skill
architect_prompt = load_skill("architect")

# Use as system prompt for your agent
response = llm.chat(
    system=architect_prompt,
    messages=[{"role": "user", "content": "Design a REST API for..."}]
)

# List all available skills
print(list_skills())
# ['architect', 'senior_dev', 'dev', 'product_owner', 'bouncer', ...]
```

## Skill Metadata

Skills include YAML frontmatter with configuration metadata:

```python
from squad_skills import load_skill_with_metadata, get_skill_metadata

# Load skill with full metadata
skill = load_skill_with_metadata("architect")
print(skill.metadata.model)         # "sonnet"
print(skill.metadata.allowed_tools) # ["Read", "Write", "Edit", "Glob", "Grep"]
print(skill.metadata.max_budget_usd) # 15.0
print(skill.content)                 # The prompt content

# Just get metadata (no content processing)
meta = get_skill_metadata("architect")
print(meta.description)  # "Designs system architecture..."
```

### SkillMetadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Skill identifier |
| `description` | str | What the skill does (for auto-invocation) |
| `model` | str | Recommended model tier: `opus`, `sonnet`, `haiku` |
| `allowed_tools` | list | Tools the agent can use |
| `max_budget_usd` | float | Cost limit per invocation |
| `disable_model_invocation` | bool | Prevent auto-invocation |
| `user_invocable` | bool | Show in `/` menu |
| `context` | str | `"fork"` for subagent execution |
| `agent` | str | Subagent type when context=fork |
| `output_template` | str | Path to output template (dir-based skills) |

## Directory-Based Skills

For complex skills that need output validation, use the directory format:

```
skills/
├── architect/
│   ├── SKILL.md              # Main instructions (with frontmatter)
│   ├── templates/
│   │   └── design_spec.yaml  # Template for structured output
│   ├── examples/
│   │   └── api_design.yaml   # Example of correct output
│   └── scripts/
│       └── validate.py       # Validation script
├── bouncer/
│   ├── SKILL.md
│   ├── templates/
│   │   └── review.yaml
│   └── ...
└── dev.md                    # Simple skills can be flat files
```

### Accessing Resources

```python
from squad_skills import load_skill_with_metadata

skill = load_skill_with_metadata("architect")

# Access templates
template = skill.resources.templates["design_spec.yaml"]

# Access examples
example = skill.resources.examples["api_design.yaml"]

# Get validation script path
validate_script = skill.resources.scripts["validate"]
```

### Output Validation

Skills can specify an output template in frontmatter:

```yaml
---
name: architect
output-template: templates/design_spec.yaml
---
```

Validation scripts can be run to verify agent output:

```bash
python scripts/validate.py agent_output.yaml
```

## Argument Substitution

Skills support `$ARGUMENTS`, `$0`, `$1`, etc. for dynamic content:

```python
from squad_skills import load_skill_with_args

# Skill content: "Fix GitHub issue $ARGUMENTS following our standards."
prompt = load_skill_with_args("fix-issue", arguments="123")
# Result: "Fix GitHub issue 123 following our standards."

# Indexed arguments
# Skill content: "Migrate $0 from $1 to $2"
prompt = load_skill_with_args("migrate", arguments=["SearchBar", "React", "Vue"])
# Result: "Migrate SearchBar from React to Vue"
```

## Dynamic Context Injection

Execute shell commands at load time with `!`command`` syntax:

```python
from squad_skills import load_skill_with_args
from pathlib import Path

# Skill content includes: !`git branch --show-current`
prompt = load_skill_with_args(
    "deploy",
    inject_commands=True,
    cwd=Path("/my/project")
)
# Commands are executed and output injected into prompt
```

## Available Skills

| Skill | Model | Role |
|-------|-------|------|
| `manager` | opus | Coordinates workflow, routes tickets, monitors confidence |
| `architect` | sonnet | Designs system architecture and interfaces |
| `product_owner` | opus | Decomposes missions into tickets with acceptance criteria |
| `scrum_master` | opus | Prioritizes backlog, assigns work, runs retrospectives |
| `bouncer` | opus | Quality gates: design review, code review, pre-prod |
| `senior_dev` | sonnet | Implements code to pass tests (TDD green phase) |
| `dev` | haiku | Writes failing tests (TDD red phase) |
| `designer` | sonnet | UX/UI design for user-facing features |
| `archaeologist` | sonnet | Researches documentation, explores codebases |
| `librarian` | haiku | Maintains documentation, runbooks, ADRs |
| `on_call` | sonnet | Operational readiness (5-25 rule), incident response |
| `qa_engineer` | sonnet | Integration tests, E2E tests, technical evals |

## Template Includes

Skills support composable fragments using `{{include path}}` syntax:

```markdown
---
name: my-agent
description: Custom agent with shared protocols
model: sonnet
allowed-tools: [Read, Write, Glob]
---

# My Custom Agent

Your role is...

{{include _common/spike_protocol.md}}
{{include _common/confidence_scoring.md}}
```

### Common Fragments

| Fragment | Purpose |
|----------|---------|
| `_common/spike_protocol.md` | Stop-the-line investigation protocol |
| `_common/assumption_logging.md` | Document assumptions and unknowns |
| `_common/confidence_scoring.md` | Output format for uncertainty |
| `_common/brownfield_protocol.md` | Respect existing codebase rules |

## Creating Custom Skills

1. Create a markdown file with YAML frontmatter
2. Use `{{include _common/...}}` for shared behavior
3. Place in your project's `.claude/skills/` directory

Example skill file:

```markdown
---
name: code-reviewer
description: Reviews code for quality and security issues
model: sonnet
allowed-tools: [Read, Grep, Glob]
max-budget-usd: 5.0
---

# Code Reviewer

Review the following code for:
1. Security vulnerabilities
2. Performance issues
3. Code style violations

{{include _common/brownfield_protocol.md}}

## Code to Review

$ARGUMENTS
```

## API Reference

```python
from squad_skills import (
    # Core loading
    load_skill,              # Load skill content (str)
    load_skill_with_metadata, # Load with SkillMetadata
    load_skill_with_args,    # Load with argument substitution
    load_skill_or_default,   # Load with fallback

    # Metadata access
    get_skill_metadata,      # Get SkillMetadata only

    # Discovery
    list_skills,             # List skill names
    list_skills_with_metadata, # List with metadata

    # Cache management
    clear_cache,             # Clear LRU cache

    # Types
    SkillMetadata,           # Metadata dataclass
    SkillResources,          # Templates, examples, scripts (dir-based)
    LoadedSkill,             # Skill + metadata + resources
    SkillLoadError,          # Exception type
)
```

## Philosophy

These skills embody key principles from software engineering:

1. **Never guess** - Request spikes when uncertain
2. **Test first** - TDD red/green/refactor cycle
3. **Document assumptions** - Make implicit knowledge explicit
4. **Quantify confidence** - Help humans know when to intervene
5. **Respect existing code** - Brownfield > greenfield thinking

## Contributing

Skills live in `squad_skills/skills/`. To contribute:

1. Fork the repository
2. Create your skill file with frontmatter
3. Add tests for your skill
4. Submit a pull request

## License

MIT
