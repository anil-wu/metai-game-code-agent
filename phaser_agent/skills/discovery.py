"""Skill discovery service for finding relevant skills based on file patterns."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Optional

from google.adk.skills import Skill

from .loader import SkillLoader


class SkillDiscovery:
    """Discovers skills based on target file paths and patterns."""

    def __init__(self, skills_root: str | Path):
        self.skills_root = Path(skills_root)
        self._skill_cache: dict[str, Skill] = {}

    def discover_skills(self, target_path: str) -> list[Skill]:
        """
        Discover skills relevant to a target file path.

        Args:
            target_path: Target file path (relative to workspace).

        Returns:
            List of matching skills sorted by priority.
        """
        matched_skills = []

        if not self.skills_root.exists():
            return []

        for skill_dir in self.skills_root.iterdir():
            if not skill_dir.is_dir():
                continue

            skill = self._load_skill(skill_dir)
            if not skill:
                continue

            file_patterns = skill.frontmatter.metadata.get("file_patterns", [])
            if isinstance(file_patterns, str):
                file_patterns = [file_patterns]

            if self._matches_patterns(target_path, file_patterns):
                matched_skills.append(skill)

        matched_skills.sort(
            key=lambda s: s.frontmatter.metadata.get("priority", 10)
        )

        print(f"Matched skills for {target_path}: {matched_skills}")
        return matched_skills

    def list_all_skills(self) -> list[Skill]:
        """List all available skills."""
        skills = []

        if not self.skills_root.exists():
            return []

        for skill_dir in self.skills_root.iterdir():
            if not skill_dir.is_dir():
                continue

            skill = self._load_skill(skill_dir)
            if skill:
                skills.append(skill)

        print(f"Found {len(skills)} skills:")
        for skill in skills:
            print(f"  - {skill.name}: {skill.frontmatter.description}")
        return skills

    def discover_by_keywords(self, keywords: list[str]) -> list[Skill]:
        """
        Discover skills based on trigger keywords.

        Args:
            keywords: List of keywords to match against skill triggers.

        Returns:
            List of matching skills.
        """
        matched_skills = []

        if not self.skills_root.exists():
            return []

        for skill_dir in self.skills_root.iterdir():
            if not skill_dir.is_dir():
                continue

            skill = self._load_skill(skill_dir)
            if not skill:
                continue

            triggers = skill.frontmatter.metadata.get("triggers", [])
            if isinstance(triggers, str):
                triggers = [triggers]

            for keyword in keywords:
                for trigger in triggers:
                    if keyword.lower() in trigger.lower():
                        matched_skills.append(skill)
                        break
        
        print(f"Matched skills for keywords {keywords}: {matched_skills}")
        return matched_skills

    def _matches_patterns(self, path: str, patterns: list[str]) -> bool:
        """Check if path matches any of the patterns."""
        if not patterns:
            return True

        for pattern in patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
            if fnmatch.fnmatch(path.lower(), pattern.lower()):
                return True
        return False

    def _load_skill(self, skill_dir: Path) -> Optional[Skill]:
        """Load a skill with caching."""
        cache_key = str(skill_dir)
        if cache_key in self._skill_cache:
            return self._skill_cache[cache_key]

        skill = SkillLoader.load_skill(skill_dir)
        if skill:
            self._skill_cache[cache_key] = skill

        return skill

    def clear_cache(self) -> None:
        """Clear the skill cache."""
        self._skill_cache.clear()
