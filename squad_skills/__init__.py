"""Squad Skills - Battle-tested agent prompts for AI development teams.

This package provides reusable, composable prompt templates for AI agents
following TDD, spike protocols, and software engineering best practices.

Usage:
    from squad_skills import load_skill, list_skills, get_skill_metadata

    # Load a specific skill (prompt content only)
    architect_prompt = load_skill("architect")

    # Load skill with metadata
    from squad_skills import load_skill_with_metadata
    skill = load_skill_with_metadata("architect")
    print(skill.metadata.model)  # "sonnet"
    print(skill.metadata.allowed_tools)  # ["Read", "Write", ...]

    # Load skill with argument substitution
    from squad_skills import load_skill_with_args
    prompt = load_skill_with_args("fix-issue", arguments="123")

    # List available skills
    available = list_skills()

    # List skills with metadata
    from squad_skills import list_skills_with_metadata
    for skill in list_skills_with_metadata():
        print(f"{skill.name}: {skill.model}")
"""

from .loader import (
    LoadedSkill,
    SkillLoadError,
    SkillMetadata,
    SkillResources,
    clear_cache,
    get_skill_metadata,
    list_skills,
    list_skills_with_metadata,
    load_skill,
    load_skill_or_default,
    load_skill_with_args,
    load_skill_with_metadata,
)

__version__ = "0.1.0"
__all__ = [
    # Core functions
    "load_skill",
    "load_skill_with_metadata",
    "load_skill_with_args",
    "load_skill_or_default",
    "get_skill_metadata",
    "list_skills",
    "list_skills_with_metadata",
    "clear_cache",
    # Types
    "SkillMetadata",
    "SkillResources",
    "LoadedSkill",
    "SkillLoadError",
]
