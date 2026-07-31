"""
Backwards-compatible bridge for app.dependencies.deps.get_current_app.
"""

from app.dependencies.deps import get_current_app

__all__ = ["get_current_app"]