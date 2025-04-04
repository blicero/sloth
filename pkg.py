#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-05 16:58:35 krylon>
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
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Final, Optional

from sloth import common, probe

BLANK: Final[str] = " "


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


@dataclass(slots=True, kw_only=True)
class Package:
    """Package (usually) is a piece of software or documentation that can be installed on a system."""

    name: str
    desc: str
    kind: Optional[str] = None
    version: Optional[str] = None
    info: Optional[str] = None


class PackageManager(ABC):
    """Base class for the different package managers."""

    __slots__ = [
        "platform",
        "log",
        "sudo",
        "output",
    ]

    platform: probe.Platform
    log: logging.Logger
    sudo: Optional[str]
    output: tuple[str, str]

    def __init__(self) -> None:
        self.platform = probe.guess_os()
        self.log = common.get_logger("PackageManager")
        self.log.debug("Running on %s", self.platform.name)
        self.output = ('', '')
        if not self.is_root():
            self.sudo = probe.find_sudo()
            if self.sudo is not None:
                self.log.debug("Using %s to run commands with elevated privileges.",
                               self.sudo)
            else:
                self.log.warning("We are not running as root, and neither sudo nor doas was found.")

    @classmethod
    def create(cls) -> 'PackageManager':
        """Return the appropriate PackageManager for the current system"""
        system = probe.guess_os()
        match system[0].lower():
            case "debian" | "ubuntu":
                return APT()
            case "opensuse-tumbleweed" | "opensuse-leap" | "opensuse":
                return Zypper()
            case "arch":
                return Pacman()
            case _:
                raise RuntimeError(f"Unsupported platform: {system[0]}")

    @abstractmethod
    def pkg_cmd(self) -> list[str]:
        """Return the command to execute the package manager."""

    @abstractmethod
    def refresh(self, **kwargs) -> None:
        """Update the local list of packages."""

    @abstractmethod
    def install(self, *args, **kwargs) -> None:
        """Install one or several packages.

        This may, obviously, cause additional packages to get installed
        as dependencies.
        """

    @abstractmethod
    def upgrade(self, **kwargs) -> None:
        """Install any pending updates."""

    @abstractmethod
    def search(self, *arg, **kwargs) -> list[Package]:
        """Search for available packages."""

    def is_root(self) -> bool:
        """Return true if we are running with root privileges."""
        return os.geteuid() == 0

    def _run(self, cmd: list[str], capture: bool = False) -> bool:
        """Execute the given command."""
        cmd = self.pkg_cmd() + cmd

        self.log.debug("Execute %s",
                       " ".join(cmd))

        proc = subprocess.run(cmd,
                              capture_output=capture,
                              text=True,
                              check=False,
                              encoding="utf-8")

        if capture:
            self.output = (proc.stdout, proc.stderr)

        if proc.returncode != 0:
            self.log.error("Error running package refresh:\n%s",
                           proc.stderr)
            return False

        return True


aptPat: Final[re.Pattern] = re.compile(r"""
^ ([^/\n]+) / (\S+) \s+         # Newline, package name, slash, branch
(\S+) \s+ \w+ \s*               # Version, arch
(?:\[ ( [^]]+ ) \] | ) $        # Installed, and if so, as a dependency?
\s+ ([^\n]+) $                  # Description
""",
                                       re.X | re.M | re.S)


class APT(PackageManager):
    """APT is a frontend for the APT package manager used on Debian and derivatives."""

    def pkg_cmd(self) -> list[str]:
        """Return the command to execute the package manager."""
        if self.sudo is not None:
            return [self.sudo, "apt"]
        return ["apt"]

    def refresh(self, **kwargs) -> None:
        """Update the local list of packages."""
        cmd = ["update"]
        self._run(cmd)

    def upgrade(self, **kwargs) -> None:
        """Install any pending updates."""
        cmd = ["full-upgrade"]
        self._run(cmd)

    def install(self, *args, **kwargs) -> None:
        """Install one or more packages."""
        self.log.debug("Install %s",
                       ", ".join(args))
        raise NotImplementedError("Installing packages is not implemented, yet.")

    def search(self, *args, **kwargs) -> list[Package]:
        """Search for available packages."""
        self.log.debug("Search %s", BLANK.join(args))
        cmd: list[str] = []
        cmd.append("search")
        cmd.extend(args)
        self._run(cmd, True)
        m = aptPat.findall(self.output[0])
        results: list[Package] = []
        if len(m) == 0:
            self.log.error("Cannot parse output of APT:\n%s\n%s",
                           self.output[0],
                           self.output[1])
        else:
            for group in m:
                info: str = ""
                match group[3].lower():
                    case "installiert":
                        info = "i"
                    case "installiert,automatisch":
                        info = "i+"
                    case "":
                        pass
                    case _:
                        self.log.debug("Unexpected info field for %s: '%s'",
                                       group[0],
                                       group[3])
                p: Package = Package(name=group[0],
                                     desc=group[4],
                                     kind=group[1],
                                     info=info,
                                     version=group[2],)
                results.append(p)
        return results


zyppPat: Final[re.Pattern] = re.compile(r"^ ([^-|\n]+) \| \s+ (\S+) \s+ \| \s+ ([^|]+) \s+ \| \s+ (\S+) \s* $", re.X | re.M)


class Zypper(PackageManager):
    """Zypper is the package manager used by openSUSE."""

    def pkg_cmd(self) -> list[str]:
        """Return the command to execute the package manager."""
        cmd: list[str] = [] if self.sudo is None else [self.sudo]
        cmd.append("zypper")
        return cmd

    def refresh(self, **kwargs) -> None:
        """Update the local list of packages."""
        cmd = ["ref"]

        if "force" in kwargs and kwargs["force"]:
            cmd.append("-f")

        self._run(cmd)

    def upgrade(self, **kwargs) -> None:
        """Install any pending updates."""
        cmd: list[str] = ["dup"] if self.platform.name == "opensuse-tumbleweed" else ["up"]
        self._run(cmd)

    def install(self, *args, **kwargs) -> None:
        """Install one or more packages."""
        self.log.debug("Install %s",
                       ", ".join(args))
        raise NotImplementedError("Installing packages is not implemented, yet.")

    def search(self, *args, **kwargs) -> list[Package]:
        """Search the package database."""
        self.log.debug("Search %s", BLANK.join(args))
        cmd: list[str] = []
        cmd.append("se")
        cmd.extend(args)
        if not self._run(cmd, True):
            self.log.error("Search for '%s' failed:\n%s",
                           BLANK.join(args),
                           self.output[1])
            return []

        m = zyppPat.findall(self.output[0])
        results: list[Package] = []
        if len(m) == 0:
            self.log.error("Cannot parse output of zypper:\n%s",
                           self.output[0])
        else:
            # First match contains the column headers, so we skip those
            for group in m[1:]:
                p: Package = Package(name=group[1],
                                     desc=group[2].strip(),
                                     kind=group[3],
                                     info=group[0].strip())
                results.append(p)
        return results


pacPat: Final[re.Pattern] = re.compile(r"""
^([^/]+) / (\S+) \s+   # repo, package name
(.*?)                  # version
(?: \s+ \[(\w+)\])?    # installed?
\n\s+ (.*)             # description
""",
                                       re.X | re.M)


class Pacman(PackageManager):
    """Pacman is a frontend to Arch Linux' pacman"""

    def pkg_cmd(self) -> list[str]:
        """Return the command to execute the package manager."""
        if self.sudo:
            return [self.sudo, "pacman"]
        return ["pacman"]

    def refresh(self, **kwargs) -> None:
        """Update the local package database"""
        cmd = ["-Sy"]
        self._run(cmd)

    def upgrade(self, **kwargs) -> None:
        """Install pending updates"""
        cmd = ["-Syu"]
        self._run(cmd)

    def install(self, *args, **kwargs) -> None:
        """Install packages"""
        cmd = ["-S"] + args
        self._run(cmd)

    def search(self, *args, **kwargs) -> list[Package]:
        """Search for available packages"""
        self.log.debug("Search %s", BLANK.join(args))
        cmd: list[str] = ["-Ss"]
        cmd.extend(args)
        self._run(cmd, True)
        m = pacPat.findall(self.output[0])
        if not m:
            self.log.debug("No results were found for '%s'", BLANK.join(args))
            return []

        results: list[Package] = []

        for group in m:
            if len(group) == 5:
                p = Package(name=group[1],
                            desc=group[4],
                            version=group[2],
                            kind=group[0],
                            info=group[3])
                results.append(p)
            else:
                p = Package(name=group[1],
                            desc=group[3],
                            version=group[2],
                            kind=group[0])
                results.append(p)

        return results

# Local Variables: #
# python-indent: 4 #
# End: #
