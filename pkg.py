#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-01 19:57:52 krylon>
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

import logging
import os
import subprocess
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Optional

from sloth import common, probe


# pylint: disable-msg=C0103
class Operation(Enum):
    """Symbolic constants to represent the various operations we might perform."""

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
    log: logging.Logger
    sudo: Optional[str]

    def __init__(self) -> None:
        self.platform = probe.guess_os()
        self.log = common.get_logger("PackageManager")
        self.log.debug("Running on %s", self.platform.name)
        if not self.is_root():
            self.sudo = probe.find_sudo()
            if self.sudo is not None:
                self.log.debug("Using %s to run commands with elevated privileges.",
                               self.sudo)
            else:
                self.log.warning("We are not running as root, and neither sudo nor doas was found.")

    @abstractmethod
    def pkg_cmd(self) -> list[str]:
        """Return the command to execute the package manager."""

    @abstractmethod
    def refresh(self, **kwargs) -> None:
        """Update the local list of packages."""

    @abstractmethod
    def install(self, **kwargs) -> None:
        """Install one or several packages.

        This may, obviously, cause additional packages to get installed
        as dependencies.
        """

    @abstractmethod
    def upgrade(self, **kwargs) -> None:
        """Install any pending updates."""

    def is_root(self) -> bool:
        """Return true if we are running with root privileges."""
        return os.geteuid() == 0

    def _run(self, cmd: list[str]) -> bool:
        """Execute the given command."""
        cmd = self.pkg_cmd() + cmd

        self.log.debug("Execute %s",
                       " ".join(cmd))

        proc = subprocess.run(cmd,
                              capture_output=True,
                              text=True,
                              check=False,
                              encoding="utf-8")

        if proc.returncode != 0:
            self.log.error("Error running package refresh:\n%s",
                           proc.stderr)
            return False
        return True


class APT(PackageManager):
    """APT is a frontend for the APT package manager used on Debian and derivatives."""

    def pkg_cmd(self) -> list[str]:
        """Return the command to execute the package manager."""
        if self.sudo is not None:
            return [self.sudo, "apt"]
        return ["apt"]

    def refresh(self, **kwargs) -> None:
        """Update the local list of packages."""
        cmd = self.pkg_cmd()
        cmd.append("update")
        self._run(cmd)

    def upgrade(self, **kwargs) -> None:
        """Install any pending updates."""
        cmd = self.pkg_cmd()
        cmd.append("full-upgrade")
        self._run(cmd)


class Zypper(PackageManager):
    """Zypper is the package manager used by openSUSE."""

    def pkg_cmd(self) -> list[str]:
        """Return the command to execute the package manager."""
        cmd: list[str] = [] if self.sudo is None else [self.sudo]
        cmd.append("zypper")
        return cmd

    def refresh(self, **kwargs) -> None:
        """Update the local list of packages."""
        cmd = self.pkg_cmd()
        cmd.append("ref")

        if "force" in kwargs and kwargs["force"]:
            cmd.append("-f")

        self._run(cmd)

# Local Variables: #
# python-indent: 4 #
# End: #
