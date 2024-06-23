"""
HOPS DLL Utilities Package

This package contains utilities and drivers for coherent lasers that use CohrHOPS DLL files.

Modules:
- hops_device: Contains the HOPSDevice class for interacting with HOPS DLL files.

Setup:
1. Download the required DLL files from the release assets on GitHub.
2. Place the DLL files in the 'dll' directory within this package.
"""

from .hops_device import HOPSDevice

__all__ = ['HOPSDevice']

__version__ = '0.0.1'

import os

# Ensure the DLL directory exists
DLL_DIR = os.path.join(os.path.dirname(__file__), 'dll')
if not os.path.exists(DLL_DIR):
    os.makedirs(DLL_DIR)

# Add the DLL directory to the DLL search path
os.add_dll_directory(DLL_DIR)
