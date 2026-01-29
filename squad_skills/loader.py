"""Skill loader for agent prompts.

Loads agent prompts from markdown skill files with support for:
- YAML frontmatter with agent metadata
- Template includes ({{include path/to/file.md}})
- Argument substitution ($ARGUMENTS, $0, $1, etc.)
- Dynamic context injection (!`command`)
- Directory-based skills with templates, examples, and validation scripts

Supports two skill formats:
1. File-based: skills/architect.md
2. Directory-based: skills/architect/SKILL.md (with templates/, examples/, scripts/)
"""

import re
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

# Directory containing skill files
SKILLS_DIR = Path(__file__).parent / "skills"

# Pattern for include directives: {{include path/to/file.md}}
INCLUDE_PATTERN = re.compile(r"\{\{include\s+([^}]+)\}\}")

# Pattern for YAML frontmatter
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Pattern for argument substitution: $ARGUMENTS, $ARGUMENTS[0], $0, $1, etc.
ARGS_PATTERN = re.compile(r"\$ARGUMENTS(?:\[(\d+)\])?|\$(\d+)")

# Pattern for dynamic command injection: !`command`
COMMAND_PATTERN = re.compile(r"!`([^`]+)`")


class SkillLoadError(Exception):
    """Raised when a skill file cannot be loaded."""

    pass


@dataclass
class SkillMetadata:
    """Metadata extracted from skill frontmatter."""

    name: str
    description: str = ""
    model: str = "sonnet"  # opus | sonnet | haiku
    allowed_tools: list[str] = field(default_factory=list)
    max_budget_usd: float = 10.0
    # Additional optional fields
    disable_model_invocation: bool = False
    user_invocable: bool = True
    context: str | None = None  # "fork" for subagent execution
    agent: str | None = None  # subagent type when context=fork
    output_template: str | None = None  # path to output template (relative to skill dir)


@dataclass
class SkillResources:
    """Resources available in directory-based skills."""

    templates: dict[str, str] = field(default_factory=dict)  # name -> content
    examples: dict[str, str] = field(default_factory=dict)  # name -> content
    scripts: dict[str, Path] = field(default_factory=dict)  # name -> path


@dataclass
class LoadedSkill:
    """A fully loaded skill with metadata and content."""

    metadata: SkillMetadata
    content: str  # The prompt content (without frontmatter)
    raw_content: str  # Original content with frontmatter
    resources: SkillResources = field(default_factory=SkillResources)  # dir-based resources
    skill_dir: Path | None = None  # directory path for dir-based skills


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from content.

    Args:
        content: Full file content

    Returns:
        Tuple of (frontmatter dict, remaining content)
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content

    frontmatter_text = match.group(1)
    remaining_content = content[match.end() :]

    # Simple YAML parsing (no external dependency)
    frontmatter: dict[str, Any] = {}
    for line in frontmatter_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            # Parse lists: [item1, item2]
            if value.startswith("[") and value.endswith("]"):
                items = value[1:-1].split(",")
                frontmatter[key] = [item.strip() for item in items if item.strip()]
            # Parse booleans
            elif value.lower() == "true":
                frontmatter[key] = True
            elif value.lower() == "false":
                frontmatter[key] = False
            # Parse numbers
            elif value.replace(".", "").replace("-", "").isdigit():
                frontmatter[key] = float(value) if "." in value else int(value)
            else:
                frontmatter[key] = value

    return frontmatter, remaining_content


def _extract_metadata(frontmatter: dict[str, Any], skill_name: str) -> SkillMetadata:
    """Extract SkillMetadata from parsed frontmatter."""
    return SkillMetadata(
        name=frontmatter.get("name", skill_name),
        description=frontmatter.get("description", ""),
        model=frontmatter.get("model", "sonnet"),
        allowed_tools=frontmatter.get("allowed-tools", []),
        max_budget_usd=float(frontmatter.get("max-budget-usd", 10.0)),
        disable_model_invocation=frontmatter.get("disable-model-invocation", False),
        user_invocable=frontmatter.get("user-invocable", True),
        context=frontmatter.get("context"),
        agent=frontmatter.get("agent"),
        output_template=frontmatter.get("output-template"),
    )


def _load_skill_resources(skill_dir: Path) -> SkillResources:
    """Load resources from a directory-based skill.

    Args:
        skill_dir: Directory containing the skill

    Returns:
        SkillResources with templates, examples, and script paths
    """
    resources = SkillResources()

    # Load templates
    templates_dir = skill_dir / "templates"
    if templates_dir.exists():
        for template_file in templates_dir.glob("*"):
            if template_file.is_file():
                resources.templates[template_file.name] = template_file.read_text()

    # Load examples
    examples_dir = skill_dir / "examples"
    if examples_dir.exists():
        for example_file in examples_dir.glob("*"):
            if example_file.is_file():
                resources.examples[example_file.name] = example_file.read_text()

    # Store script paths (don't load content, just paths for execution)
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        for script_file in scripts_dir.glob("*"):
            if script_file.is_file():
                resources.scripts[script_file.stem] = script_file

    return resources


def _find_skill_path(skill_name: str) -> tuple[Path, bool]:
    """Find the skill file or directory.

    Args:
        skill_name: Name of the skill

    Returns:
        Tuple of (path, is_directory)

    Raises:
        SkillLoadError: If skill not found
    """
    # Check for directory-based skill first (preferred)
    skill_dir = SKILLS_DIR / skill_name
    if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
        return skill_dir, True

    # Fall back to file-based skill
    skill_file = SKILLS_DIR / f"{skill_name}.md"
    if skill_file.exists():
        return skill_file, False

    raise SkillLoadError(
        f"Skill not found: {skill_name}. Tried: {skill_dir}/SKILL.md and {skill_file}"
    )


def _resolve_includes(content: str, base_dir: Path, seen: set[Path] | None = None) -> str:
    """Recursively resolve {{include}} directives in content.

    Args:
        content: The content to process
        base_dir: Base directory for resolving relative paths
        seen: Set of already-included paths (for cycle detection)

    Returns:
        Content with all includes resolved

    Raises:
        SkillLoadError: If include cycle detected or file not found
    """
    if seen is None:
        seen = set()

    def replace_include(match: re.Match) -> str:
        include_path = match.group(1).strip()
        full_path = (base_dir / include_path).resolve()

        # Cycle detection
        if full_path in seen:
            raise SkillLoadError(f"Circular include detected: {full_path}")

        if not full_path.exists():
            raise SkillLoadError(f"Include file not found: {full_path}")

        seen.add(full_path)

        # Load and recursively process the included file
        included_content = full_path.read_text()
        return _resolve_includes(included_content, full_path.parent, seen)

    return INCLUDE_PATTERN.sub(replace_include, content)


def _substitute_arguments(content: str, arguments: str | list[str] | None) -> str:
    """Substitute $ARGUMENTS, $ARGUMENTS[N], and $N placeholders.

    Args:
        content: Content with argument placeholders
        arguments: Either a string (all args) or list of individual args

    Returns:
        Content with arguments substituted
    """
    if arguments is None:
        arguments = []
    elif isinstance(arguments, str):
        # Split string into list for indexed access
        args_list = arguments.split() if arguments else []
        args_str = arguments
    else:
        args_list = list(arguments)
        args_str = " ".join(arguments)

    def replace_arg(match: re.Match) -> str:
        # $ARGUMENTS[N] or $N
        if match.group(1) is not None:
            idx = int(match.group(1))
            return args_list[idx] if idx < len(args_list) else ""
        elif match.group(2) is not None:
            idx = int(match.group(2))
            return args_list[idx] if idx < len(args_list) else ""
        # Plain $ARGUMENTS
        return args_str

    result = ARGS_PATTERN.sub(replace_arg, content)

    # If $ARGUMENTS wasn't in content but args were provided, append them
    if arguments and "$ARGUMENTS" not in content and "$0" not in content:
        result = f"{result}\n\nARGUMENTS: {args_str}"

    return result


def _inject_dynamic_context(content: str, cwd: Path | None = None) -> str:
    """Execute !`command` placeholders and inject output.

    Args:
        content: Content with command placeholders
        cwd: Working directory for command execution

    Returns:
        Content with command outputs injected
    """

    def run_command(match: re.Match) -> str:
        command = match.group(1)
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd,
            )
            return (
                result.stdout.strip()
                if result.returncode == 0
                else f"[Error: {result.stderr.strip()}]"
            )
        except subprocess.TimeoutExpired:
            return "[Error: Command timed out]"
        except Exception as e:
            return f"[Error: {e}]"

    return COMMAND_PATTERN.sub(run_command, content)


@lru_cache(maxsize=32)
def load_skill(skill_name: str) -> str:
    """Load a skill file and resolve all includes.

    Args:
        skill_name: Name of the skill (without .md extension)
                   e.g., "architect", "senior_dev", "bouncer"

    Returns:
        The fully resolved prompt content (without frontmatter)

    Raises:
        SkillLoadError: If skill file not found or include error
    """
    loaded = load_skill_with_metadata(skill_name)
    return loaded.content


def load_skill_with_metadata(skill_name: str) -> LoadedSkill:
    """Load a skill file with metadata.

    Supports both file-based (skill.md) and directory-based (skill/SKILL.md) formats.

    Args:
        skill_name: Name of the skill (without .md extension)

    Returns:
        LoadedSkill with metadata, content, and resources (for dir-based)

    Raises:
        SkillLoadError: If skill file not found or include error
    """
    skill_path, is_directory = _find_skill_path(skill_name)

    if is_directory:
        # Directory-based skill
        skill_file = skill_path / "SKILL.md"
        raw_content = skill_file.read_text()

        # Parse frontmatter
        frontmatter, content = _parse_frontmatter(raw_content)
        metadata = _extract_metadata(frontmatter, skill_name)

        # Resolve includes (relative to skills dir for _common/)
        content = _resolve_includes(content, SKILLS_DIR)

        # Load resources
        resources = _load_skill_resources(skill_path)

        return LoadedSkill(
            metadata=metadata,
            content=content,
            raw_content=raw_content,
            resources=resources,
            skill_dir=skill_path,
        )
    else:
        # File-based skill
        raw_content = skill_path.read_text()

        # Parse frontmatter
        frontmatter, content = _parse_frontmatter(raw_content)
        metadata = _extract_metadata(frontmatter, skill_name)

        # Resolve includes
        content = _resolve_includes(content, SKILLS_DIR)

        return LoadedSkill(
            metadata=metadata,
            content=content,
            raw_content=raw_content,
        )


def load_skill_with_args(
    skill_name: str,
    arguments: str | list[str] | None = None,
    inject_commands: bool = False,
    cwd: Path | None = None,
) -> str:
    """Load a skill with argument substitution and optional command injection.

    Args:
        skill_name: Name of the skill
        arguments: Arguments to substitute ($ARGUMENTS, $0, etc.)
        inject_commands: Whether to execute !`command` placeholders
        cwd: Working directory for command execution

    Returns:
        Fully processed skill content
    """
    loaded = load_skill_with_metadata(skill_name)
    content = loaded.content

    # Substitute arguments
    if arguments is not None:
        content = _substitute_arguments(content, arguments)

    # Inject dynamic context
    if inject_commands:
        content = _inject_dynamic_context(content, cwd)

    return content


def get_skill_metadata(skill_name: str) -> SkillMetadata:
    """Get just the metadata for a skill without full content processing.

    Args:
        skill_name: Name of the skill

    Returns:
        SkillMetadata for the skill
    """
    return load_skill_with_metadata(skill_name).metadata


def load_skill_or_default(skill_name: str, default: str) -> str:
    """Load a skill file, falling back to default if not found.

    Args:
        skill_name: Name of the skill
        default: Default prompt to use if skill file doesn't exist

    Returns:
        The skill content or default
    """
    try:
        return load_skill(skill_name)
    except SkillLoadError:
        return default


def list_skills() -> list[str]:
    """List all available skills (both file-based and directory-based).

    Returns:
        List of skill names
    """
    if not SKILLS_DIR.exists():
        return []

    skills = set()

    # File-based skills: *.md files (excluding _common)
    for f in SKILLS_DIR.glob("*.md"):
        if not f.name.startswith("_"):
            skills.add(f.stem)

    # Directory-based skills: dirs with SKILL.md (excluding _common)
    for d in SKILLS_DIR.iterdir():
        if d.is_dir() and not d.name.startswith("_"):
            if (d / "SKILL.md").exists():
                skills.add(d.name)

    return sorted(skills)


def list_skills_with_metadata() -> list[SkillMetadata]:
    """List all skills with their metadata.

    Returns:
        List of SkillMetadata for all available skills
    """
    return [get_skill_metadata(name) for name in list_skills()]


def clear_cache() -> None:
    """Clear the skill loading cache.

    Useful for development/testing when skill files change.
    """
    load_skill.cache_clear()
