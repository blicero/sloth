#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-12-18 20:30:35 krylon>
#
# /data/code/python/sloth/pkg.py
# created on 18. 12. 2023
# (c) 2023 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
sloth.pkg

(c) 2023 Benjamin Walkenhorst
"""

from abc import ABC
from enum import Enum, auto
from typing import Final

from sloth import probe


class Operation(Enum):
    """Symbolic constants to represent the various operations
    we might perform."""
    Install = auto()
    Delete = auto()
    Refresh = auto()
    Upgrade = auto()
    UpgradeBig = auto()
    UpgradeRelease = auto()
    Cleanup = auto()
    Autoremove = auto()


class PackageManager(ABC):
    """Base class for the different package managers."""

    platform: Final[probe.Platform]


# Local Variables: #
# python-indent: 4 #
# End: #