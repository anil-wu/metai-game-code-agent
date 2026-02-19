"""Skill registry for managing skill lifecycle and caching."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from google.adk.skills import Frontmatter
from google.adk.skills import Skill

from .discovery import SkillDiscovery


class SkillRegistry:
    """Singleton registry for managing skills."""

    _instance: Optional["SkillRegistry"] = None

    def __init__(self, skills_root: str | Path):
        self.skills_root = Path(skills_root)
        self._skills: dict[str, Skill] = {}
        self._discovery = SkillDiscovery(skills_root)

    @classmethod
    def get_instance(cls, skills_root: str | Path | None = None) -> "SkillRegistry":
        """Get the singleton instance."""
        if cls._instance is None:
            if skills_root is None:
                raise ValueError("skills_root required for first initialization")
            cls._instance = cls(skills_root)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None

    def register_skill(self, skill: Skill) -> None:
        """Register a skill."""
        print(f"Registering skill: {skill.name}")
        self._skills[skill.name] = skill

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        if name not in self._skills:
            self._load_skill_by_name(name)
        return self._skills.get(name)

    def list_skills(self) -> list[Frontmatter]:
        """List all skill frontmatter metadata."""
        self._ensure_loaded()
        return [s.frontmatter for s in self._skills.values()]

    def list_all_skills(self) -> list[Skill]:
        """List all skills."""
        self._ensure_loaded()
        return list(self._skills.values())

    def discover_for_path(self, target_path: str) -> list[Skill]:
        """Discover skills for a target path."""
        return self._discovery.discover_skills(target_path)

    def discover_by_keywords(self, keywords: list[str]) -> list[Skill]:
        """Discover skills by keywords."""
        return self._discovery.discover_by_keywords(keywords)

    def _load_skill_by_name(self, name: str) -> None:
        """Load a skill by name from the file system."""
        skill_dir = self.skills_root / name
        if not skill_dir.exists():
            return

        skill = self._discovery._load_skill(skill_dir)
        if skill:
            self._skills[name] = skill

    def _ensure_loaded(self) -> None:
        """Ensure all skills are loaded."""
        if not self._skills:
            for skill in self._discovery.list_all_skills():
                self._skills[skill.name] = skill

    def clear_cache(self) -> None:
        """Clear all cached skills."""
        self._skills.clear()
        self._discovery.clear_cache()
