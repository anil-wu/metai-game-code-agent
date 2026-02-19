"""Skill loader for parsing SKILL.md files and loading resources."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

from google.adk.skills import Frontmatter
from google.adk.skills import Resources
from google.adk.skills import Script
from google.adk.skills import Skill


class SkillLoader:
    """Loads skills from the file system."""

    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)

    @classmethod
    def parse_skill_md(cls, skill_md_path: Path) -> tuple[dict, str]:
        """
        Parse a SKILL.md file.

        Args:
            skill_md_path: Path to the SKILL.md file.

        Returns:
            Tuple of (frontmatter_dict, body_content).
        """
        content = skill_md_path.read_text(encoding="utf-8")
        match = cls.FRONTMATTER_PATTERN.match(content)

        if not match:
            return {}, content.strip()

        frontmatter_yaml = match.group(1)
        body = match.group(2).strip()

        frontmatter = yaml.safe_load(frontmatter_yaml) or {}

        print(f"Parsed frontmatter for {skill_md_path}: {frontmatter}")
        return frontmatter, body

    @classmethod
    def validate_frontmatter(cls, frontmatter: dict) -> list[str]:
        """Validate frontmatter required fields."""
        errors = []

        if not frontmatter.get("name"):
            errors.append("Missing required field: name")

        if not frontmatter.get("description"):
            errors.append("Missing required field: description")

        name = frontmatter.get("name", "")
        if name and not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
            errors.append(f"Invalid name format, expected kebab-case: {name}")

        return errors

    @classmethod
    def load_resources(cls, skill_dir: Path) -> Resources:
        """Load skill resources from references/, assets/, and scripts/ directories."""
        resources = Resources()

        refs_dir = skill_dir / "references"
        if refs_dir.exists():
            for ref_file in refs_dir.glob("**/*.md"):
                rel_path = str(ref_file.relative_to(refs_dir))
                resources.references[rel_path] = ref_file.read_text(encoding="utf-8")

        assets_dir = skill_dir / "assets"
        if assets_dir.exists():
            for asset_file in assets_dir.glob("**/*"):
                if asset_file.is_file():
                    rel_path = str(asset_file.relative_to(assets_dir))
                    try:
                        resources.assets[rel_path] = asset_file.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        pass

        scripts_dir = skill_dir / "scripts"
        if scripts_dir.exists():
            for script_file in scripts_dir.glob("**/*"):
                if script_file.is_file():
                    rel_path = str(script_file.relative_to(scripts_dir))
                    try:
                        content = script_file.read_text(encoding="utf-8")
                        resources.scripts[rel_path] = Script(src=content)
                    except UnicodeDecodeError:
                        pass

        return resources

    @classmethod
    def _normalize_metadata(cls, metadata: dict) -> dict[str, str]:
        """Convert metadata values to strings for ADK compatibility."""
        result: dict[str, str] = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                result[key] = value
            elif isinstance(value, list):
                result[key] = ",".join(str(v) for v in value)
            else:
                result[key] = str(value)
        return result

    @classmethod
    def load_skill(cls, skill_dir: Path) -> Optional[Skill]:
        """
        Load a skill from a directory.

        Args:
            skill_dir: Path to the skill directory containing SKILL.md.

        Returns:
            Skill object or None if loading fails.
        """
        skill_dir = skill_dir.resolve()

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return None

        try:
            frontmatter_dict, body = cls.parse_skill_md(skill_md)

            errors = cls.validate_frontmatter(frontmatter_dict)
            if errors:
                print(f"Skill validation errors in {skill_dir}: {errors}")
                return None

            raw_metadata = frontmatter_dict.get("metadata", {})
            if not isinstance(raw_metadata, dict):
                raw_metadata = {}
            metadata = cls._normalize_metadata(raw_metadata)

            allowed_tools = frontmatter_dict.get("allowed_tools")
            if isinstance(allowed_tools, list):
                allowed_tools = ",".join(allowed_tools)

            frontmatter = Frontmatter(
                name=frontmatter_dict["name"],
                description=frontmatter_dict["description"],
                license=frontmatter_dict.get("license"),
                compatibility=frontmatter_dict.get("compatibility"),
                allowed_tools=allowed_tools,
                metadata=metadata,
            )

            resources = cls.load_resources(skill_dir)

            return Skill(
                frontmatter=frontmatter,
                instructions=body,
                resources=resources,
            )

        except Exception as e:
            print(f"Error loading skill from {skill_dir}: {e}")
            return None
