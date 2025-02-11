"""
HOPS DLL Utilities Package

This package contains utilities and drivers for coherent lasers that use CohrHOPS DLL files.

Setup:
1. Download the required DLL files from the release assets on GitHub.
2. Place the DLL files in this package alongside the respective .h files.
"""

from .cohrhops import CohrHOPSDevice, CohrHOPSManager, HOPSException, get_cohrhops_manager

__all__ = ["CohrHOPSDevice", "CohrHOPSManager", "HOPSException", "get_cohrhops_manager"]
