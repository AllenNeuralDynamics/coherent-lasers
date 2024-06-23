"""
Driver for Coherent Genesis MX series lasers.

Setup:
- If using the HOPSDevice class, ensure the CohrHOPS DLL files are in the 'dll' directory within the 'common/hops'
package.

Classes:
- GenesisMX: Driver for Coherent Genesis MX series lasers.
- GenesisMXOperationModes: Enum for Genesis MX operation modes.
- GenesisMXAlarms: Enum for Genesis MX alarms.
- GenesisMXReadCmds: Enum for Genesis MX read commands.
- GenesisMXWriteCmds: Enum for Genesis MX write commands.
- GenesisMXVoxelLaser: Voxel wraper for GenesisMX class.
"""

from .commands import (ReadCmds as GenesisMXReadCmds,
                       WriteCmds as GenesisMXWriteCmds,
                       OperationModes as GenesisMXOperationModes,
                       Alarms as GenesisMXAlarms
                       )
from .genesis_mx import GenesisMX
from .genesis_mx_voxel import GenesisMXVoxelLaser

__all__ = [
    'GenesisMX',
    'GenesisMXVoxelLaser',
    'GenesisMXOperationModes',
    'GenesisMXAlarms',
    'GenesisMXReadCmds',
    'GenesisMXWriteCmds'
]
