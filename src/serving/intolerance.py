"""
Intolerance module — re-exports ``IntoleranceDetector`` from memory
for convenience (serving pipeline imports from here).
"""

from src.memory.client_profile import IntoleranceDetector

__all__ = ["IntoleranceDetector"]
