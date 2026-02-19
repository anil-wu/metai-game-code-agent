"""Skills system for Phaser Agent.

This module provides skill loading, discovery, and registry functionality
that integrates with Google ADK's SkillToolset.
"""

from .discovery import SkillDiscovery
from .loader import SkillLoader
from .registry import SkillRegistry

__all__ = [
    "SkillLoader",
    "SkillDiscovery",
    "SkillRegistry",
]
