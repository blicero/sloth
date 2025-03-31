#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-03-31 23:51:40 krylon>
#
# /data/code/python/sloth/pkg.py
# created on 18. 12. 2023
# (c) 2023 Benjamin Walkenhorst
#
# This file is part of the Sloth Meta Package Manager. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
sloth.pkg

(c) 2023 Benjamin Walkenhorst
"""

from abc import ABC, abstractmethod
from enum import Enum, auto

from sloth import probe


# pylint: disable-msg=C0103
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


# pylint: disable-msg=R0903
class PackageManager(ABC):
    """Base class for the different package managers."""

    platform: probe.Platform

    @abstractmethod
    def refresh(self, *args):
        """Update the local list of packages."""
        ...

    @abstractmethod
    def install(self, *args):
        """Install one or several packages.
        This may, obviously, cause additional packages to get installed
        as dependencies."""
        ...


# Local Variables: #
# python-indent: 4 #
# End: #
