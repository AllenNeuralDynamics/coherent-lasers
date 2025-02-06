"""
HOPS DLL Utilities Package

This package contains utilities and drivers for coherent lasers that use CohrHOPS DLL files.

Setup:
1. Download the required DLL files from the release assets on GitHub.
2. Place the DLL files in this package alongside the respective .h files.
"""

from .lib import HOPSDevice, get_hops_manager, HOPSException
from .cohrhops import CohrHOPSDevice, get_cohrhops_manager, HOPSCommandException

__all__ = [
    "HOPSDevice",
    "get_hops_manager",
    "HOPSException",
    "CohrHOPSDevice",
    "get_cohrhops_manager",
    "HOPSCommandException",
]
