"""
datapizza.tools.vectorspace
============================
Agent-queryable vector space tools.

Provides tools that agents can use to introspect their own position
in a behavioral feature space, query distances to strategic zones,
and reason about trajectory momentum.

Tools:
    VectorSpaceViewer  — Query positions, distances, neighbors, trajectories
    VectorSpaceDashboard — Launch a real-time web visualization
"""

from datapizza.tools.vectorspace.viewer import VectorSpaceViewer

__all__ = ["VectorSpaceViewer"]

try:
    from datapizza.tools.vectorspace.dashboard import VectorSpaceDashboard
    __all__.append("VectorSpaceDashboard")
except ImportError:
    pass  # flask not installed — dashboard unavailable
