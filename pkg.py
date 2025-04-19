#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-20 00:58:00 krylon>
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
from sloth.config import Config
from sloth.common import BLANK

try:
    import dnf
except ModuleNotFoundError:
    pass


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
    Audit = auto()
    Search = auto()


@dataclass(slots=True, kw_only=True)
class Package:
    """Package (usually) is a piece of software or documentation that can be installed on a system."""

    name: str
    desc: str
    kind: Optional[str] = None
    version: Optional[str] = None
    info: Optional[str] = None

    def __hash__(self):
        base = f"{self.name} -- {self.desc}"
        if self.version is not None:
            base += f" {self.version}"
        return hash(base)


class PackageManager(ABC):
    """Base class for the different package managers."""

    __slots__ = [
        "platform",
        "log",
        "sudo",
        "output",
        "nice",
        "yes",
    ]

    platform: probe.Platform
    log: logging.Logger
    sudo: Optional[str]
    output: tuple[str, str]
    nice: bool
    yes: bool

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

        self.__process_config()

    def __process_config(self):
        cfg = Config()
        try:
            self.nice = cfg.cfg["shell"]["nice"]
            self.yes = cfg.cfg["shell"]["say-yes"]
        except:  # noqa: B001,E722 pylint: disable-msg=W0702
            self.nice = False
            self.yes = False

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
            case "fedora" | "rocky":
                return DNF()
            case "freebsd":
                return FreeBSD()
            case "openbsd":
                return OpenBSD()
            case _:
                raise RuntimeError(f"Unsupported platform: {system[0]}")

    @abstractmethod
    def pkg_cmd(self, op: Optional[Operation] = None) -> list[str]:
        """Return the command to execute the package manager."""

    @abstractmethod
    def refresh(self, **kwargs) -> int:
        """Update the local list of packages."""

    @abstractmethod
    def install(self, *args, **kwargs) -> int:
        """Install one or several packages.

        This may, obviously, cause additional packages to get installed
        as dependencies.
        """

    @abstractmethod
    def remove(self, *args, **kwargs) -> int:
        """Remove one or more packages"""

    @abstractmethod
    def upgrade(self, **kwargs) -> int:
        """Install any pending updates."""

    @abstractmethod
    def search(self, *arg, **kwargs) -> list[Package]:
        """Search for available packages."""

    @abstractmethod
    def autoremove(self, *args, **kwargs) -> int:
        """Remove unneeded packages."""

    @abstractmethod
    def cleanup(self, *args, **kwargs) -> int:
        """Clean up downloaded packages."""

    @abstractmethod
    def audit(self, *args, **kwargs) -> list[Package]:
        """Audit installed packages for known vulnerabilities."""

    def is_root(self) -> bool:
        """Return true if we are running with root privileges."""
        return os.geteuid() == 0

    def _run(self, cmd: list[str], capture: bool = False, **kwargs) -> tuple[bool, int]:
        """Execute the given command."""
        prefix: list[str] = []
        if "op" in kwargs:
            prefix = self.pkg_cmd(kwargs["op"])
        else:
            prefix = self.pkg_cmd()
        cmd = prefix + cmd

        if self.nice:
            cmd = ["nice"] + cmd

        try:
            self.log.debug("Execute %s",
                           " ".join(cmd))
        except TypeError as err:
            self.log.error("TypeError: %s\n%s\n",
                           err,
                           cmd)

        proc = subprocess.run(cmd,
                              capture_output=capture,
                              text=True,
                              check=False,
                              encoding="utf-8")

        if capture:
            self.output = (proc.stdout, proc.stderr)

        if proc.returncode != 0:
            cmdstr: Final[str] = BLANK.join(cmd)
            self.log.error("Error running command '%s':\n%s",
                           cmdstr,
                           proc.stderr)
            return (False, proc.returncode)

        return (True, proc.returncode)


aptPat: Final[re.Pattern] = re.compile(r"""
^ ([^/\n]+) / (\S+) \s+         # Newline, package name, slash, branch
(\S+) \s+ \w+ \s*               # Version, arch
(?:\[ ( [^]]+ ) \] | ) $        # Installed, and if so, as a dependency?
\s+ ([^\n]+) $                  # Description
""",
                                       re.X | re.M | re.S)


class APT(PackageManager):
    """APT is a frontend for the APT package manager used on Debian and derivatives."""

    def pkg_cmd(self, _op: Optional[Operation] = None) -> list[str]:
        """Return the command to execute the package manager."""
        if self.sudo is not None:
            return [self.sudo, "apt"]
        return ["apt"]

    def refresh(self, **kwargs) -> int:
        """Update the local list of packages."""
        cmd = ["update"]
        _, code = self._run(cmd)
        return code

    def upgrade(self, **kwargs) -> int:
        """Install any pending updates."""
        cmd = ["full-upgrade"]
        if self.yes or "yes" in kwargs:
            cmd.append("-y")
        _, code = self._run(cmd)
        return code

    def install(self, *args, **kwargs) -> int:
        """Install one or more packages."""
        assert len(args) > 0
        self.log.debug("Install %s",
                       ", ".join(args))
        cmd = ["install"]
        if self.yes:
            cmd.append("-y")
        cmd.extend(args)
        _, code = self._run(cmd)
        return code

    def remove(self, *args, **kwargs) -> int:
        """Remove one or more packages."""
        assert len(args) > 0
        self.log.debug("Remove %s", BLANK.join(args))
        cmd = ["remove"]
        if self.yes:
            cmd.append("-y")
        cmd.extend(args)
        _, code = self._run(cmd)
        return code

    def autoremove(self, *args, **kwargs) -> int:
        """Remove unneeded packages."""
        self.log.debug("Remove unneeded packages.")
        if "purge" in args:
            cmd = ["autopurge"]
        else:
            cmd = ["autoremove"]
        if self.yes:
            cmd.append("-y")
        _, code = self._run(cmd)
        return code

    def cleanup(self, *args, **kwargs) -> int:
        """Clean up downloaded packages."""
        cmd = ["clean"]
        _, code = self._run(cmd)
        return code

    def audit(self, *args, **kwargs) -> list[Package]:
        """Audit installed packages for known vulnerabilities."""
        # We *could* configure a 3rd-party audit tool like lynis...
        print("Audit on Debian is not implemented, yet.")
        return []

    def search(self, *args, **kwargs) -> list[Package]:
        """Search for available packages."""
        self.log.debug("Search %s", BLANK.join(args))
        cmd: list[str] = ["search"]
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

    def pkg_cmd(self, _op: Optional[Operation] = None) -> list[str]:
        """Return the command to execute the package manager."""
        cmd: list[str] = [] if self.sudo is None else [self.sudo]
        cmd.append("zypper")
        return cmd

    def refresh(self, **kwargs) -> int:
        """Update the local list of packages."""
        cmd = ["ref"]

        if "force" in kwargs and kwargs["force"]:
            cmd.append("-f")

        _, code = self._run(cmd)
        return code

    def upgrade(self, **kwargs) -> int:
        """Install any pending updates."""
        cmd: list[str] = ["dup"] if self.platform.name == "opensuse-tumbleweed" else ["up"]
        if self.yes:
            cmd.append("-y")
        _, code = self._run(cmd)
        return code

    def install(self, *args, **kwargs) -> int:
        """Install one or more packages."""
        self.log.debug("Install %s",
                       ", ".join(args))
        cmd = ["install"]
        if self.yes:
            cmd.append("-y")
        cmd.extend(args)
        _, code = self._run(cmd)
        return code

    def remove(self, *args, **kwargs) -> int:
        """Remove one or more packages."""
        cmd = ["rm", "-u"]
        if self.yes:
            cmd.append("-y")
        cmd.extend(args)
        _, code = self._run(cmd)
        return code

    def autoremove(self, *args, **kwargs) -> int:
        """Remove unneeded packages."""
        self.log.info("autoremove is a no-op on zypper.")
        return 0

    def cleanup(self, *args, **kwargs) -> int:
        """Clean up downloaded packages."""
        cmd = ["clean", "--all"]
        _, code = self._run(cmd)
        return code

    def audit(self, *args, **kwargs) -> list[Package]:
        """Audit installed packages for known vulnerabilities."""
        # We *could* configure a 3rd-party audit tool like lynis...
        print("Audit on openSUSE is not implemented, yet.")
        return []

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

    def pkg_cmd(self, _op: Optional[Operation] = None) -> list[str]:
        """Return the command to execute the package manager."""
        if self.sudo:
            return [self.sudo, "pacman"]
        return ["pacman"]

    def refresh(self, **kwargs) -> int:
        """Update the local package database"""
        cmd = ["-Sy"]
        _, code = self._run(cmd)
        return code

    def upgrade(self, **kwargs) -> int:
        """Install pending updates"""
        cmd = ["-Syu"]
        _, code = self._run(cmd)
        return code

    def install(self, *args, **kwargs) -> int:
        """Install packages"""
        cmd = ["-S"] + list(args)
        _, code = self._run(cmd)
        return code

    def remove(self, *args, **kwargs) -> int:
        """Remove one or more packages."""
        cmd = ["-R"]
        cmd.extend(args)
        _, code = self._run(cmd)
        return code

    def autoremove(self, *args, **kwargs) -> int:
        """Remove unneeded packages."""
        cmd = ["-R", "-u"]
        _, code = self._run(cmd)
        return code

    def cleanup(self, *args, **kwargs) -> int:
        """Clean up downloaded packages."""
        cmd = ["-Scc"]
        _, code = self._run(cmd)
        return code

    def audit(self, *args, **kwargs) -> list[Package]:
        """Audit installed packages for known vulnerabilities."""
        # We *could* configure a 3rd-party audit tool like lynis...
        print("Audit on Arch is not implemented, yet.")
        return []

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


class DNF(PackageManager):
    """DNF is the package manager on RHEL, Fedora, and their offspring."""

    def pkg_cmd(self, _op: Optional[Operation] = None) -> list[str]:
        """Return the command to execute the package manager."""
        if self.sudo:
            return [self.sudo, "dnf"]
        return ["dnf"]

    def refresh(self, **kwargs) -> int:
        """Update the local package database"""
        # dnf does not have an explicit command to refresh its database, as far as I can tell.
        # But I suppose this is a useful approximation.
        cmd = ["--refresh", "check-update"]
        _, code = self._run(cmd)
        return code

    def upgrade(self, **kwargs) -> int:
        """Install available updates."""
        cmd = ["upgrade"]
        if self.yes:
            cmd.append("-y")
        _, code = self._run(cmd)
        return code

    def install(self, *args, **kwargs) -> int:
        """Install packages"""
        cmd = ["install"]
        if self.yes:
            cmd.append("-y")
        cmd.extend(args)
        _, code = self._run(cmd)
        return code

    def remove(self, *args, **kwargs) -> int:
        """Remove one or more packages."""
        cmd = ["remove"]
        if self.yes:
            cmd.append("-y")
        cmd.extend(args)
        _, code = self._run(cmd)
        return code

    def autoremove(self, *args, **kwargs) -> int:
        """Remove unneeded packages."""
        cmd = ["autoremove"]
        if self.yes:
            cmd.append("-y")
        _, code = self._run(cmd)
        return code

    def cleanup(self, *args, **kwargs) -> int:
        """Clean up downloaded packages."""
        cmd = ["clean all"]
        _, code = self._run(cmd)
        return code

    def audit(self, *args, **kwargs) -> list[Package]:
        """Audit installed packages for known vulnerabilities."""
        # Output of "dnf advisory list --updates":
        # Aktualisiere und lade Paketquellen:
        # Paketquellen geladen.
        # Name                   Type        Severity                                     Package              Issued
        # FEDORA-2025-811269fb5f enhancement None                    libsolv-0.7.32-4.fc41.x86_64 2025-04-05 02:45:00
        # FEDORA-2025-c6d8815d3a bugfix      Moderate          selinux-policy-41.36-1.fc41.noarch 2025-04-09 01:25:12
        # FEDORA-2025-c6d8815d3a bugfix      Moderate selinux-policy-targeted-41.36-1.fc41.noarch 2025-04-09 01:25:12
        if self.platform.name == "fedora":
            cmd = ["advisory", "list", "--updates"]
            self._run(cmd)
        else:
            print("Audit on Fedora / RHEL is not implemented, yet.")
        return []

    def search(self, *args, **kwargs) -> list[Package]:
        """Search the package database"""
        self.log.debug("Searching for %s", BLANK.join(args))
        # cmd = ["search"] + args
        # self._run(cmd, True)
        base = dnf.Base()
        base.fill_sack()
        q = base.sack.query().filter(name__substr=args[0])
        results = []
        for p in q.run():
            print(p)
            pack = Package(
                name=p.name,
                desc=p.summary,
                version=p.version,
                info="i" if p.installed else "",
                kind=p.reponame)
            results.append(pack)
        return results


pkgPat: Final[re.Pattern] = re.compile(r"""^([-_a-zA-Z0-9]+?)-(\d\S+)\s+(.*)""",
                                       re.M | re.X)


class FreeBSD(PackageManager):
    """FreeBSD provides support for the FreeBSD operating system (hence the name)."""

    def pkg_cmd(self, _op: Optional[Operation] = None) -> list[str]:
        """Return the path to the package manager."""
        if self.sudo is not None:
            return [self.sudo, "/usr/sbin/pkg"]
        return ["/usr/sbin/pkg"]

    def refresh(self, **kwargs) -> int:
        """Update the local package database."""
        cmd = ["update"]
        _, code = self._run(cmd)
        return code

    def upgrade(self, **kwargs) -> int:
        """Install available updates."""
        cmd = ["upgrade"]
        _, code = self._run(cmd)
        return code

    def install(self, *args, **kwargs) -> int:
        """Install one or more packages."""
        cmd = ["install"] + list(args)
        _, code = self._run(cmd)
        return code

    def remove(self, *args, **kwargs) -> int:
        """Remove one or more packages."""
        cmd = ["delete"]
        cmd.extend(args)
        _, code = self._run(cmd)
        return code

    def autoremove(self, *args, **kwargs) -> int:
        """Remove unneeded packages."""
        cmd = ["autoremove"]
        _, code = self._run(cmd)
        return code

    def cleanup(self, *args, **kwargs) -> int:
        """Clean up downloaded packages."""
        cmd = ["clean"]
        _, code = self._run(cmd)
        return code

    def audit(self, *args, **kwargs) -> list[Package]:
        """Audit installed packages for known vulnerabilities."""
        # pkg audit -Rjson will print the result in JSON.
        cmd = ["audit", "-F"]
        self._run(cmd)
        return []

    def search(self, *args, **kwargs) -> list[Package]:
        """Search for available packages."""
        cmd: list[str] = ["search"]
        cmd.extend(args)
        self._run(cmd, True)
        m = pkgPat.findall(self.output[0])
        results: list[Package] = []

        if len(m) == 0:
            self.log.error("Cannot parse output of pkg(8):\n%s\n%s\n",
                           self.output[0],
                           self.output[1])
        else:
            for i in m:
                p = Package(name=i[0],
                            version=i[1],
                            desc=i[2])
                results.append(p)

        return results


# Sample output of pkg_info -Q emacs on OpenBSD 7.6
# debug-emacs-29.4p0-gtk2
# debug-emacs-29.4p0-gtk3
# debug-emacs-29.4p0-no_x11
# emacs-29.4p0-gtk2
# emacs-29.4p0-gtk3
# emacs-29.4p0-no_x11 (installed)
# emacs-anthy-9100hp9
# notmuch-emacs-0.38.3p0
# uemacs-4.0p2
# xemacs-21.4.22p37
# xemacs-21.4.22p37-mule
# xemacs-sumo-21.20100727p1
# xemacs-sumo-21.20100727p1-mule

openBSDPat: Final[re.Pattern] = re.compile(r"^([-\w]+?)-(\d\S+)(?:\s+\((installed)\))?$",
                                           re.I | re.X | re.M)


class OpenBSD(PackageManager):
    """OpenBSD provides support for OpenBSD's pkg_* package management."""

    def _cmd(self, op: Operation) -> str:
        """Return the appropriate command for the operation."""
        match op:
            case Operation.Install | Operation.Upgrade | Operation.UpgradeBig | Operation.UpgradeRelease:
                return "/usr/sbin/pkg_add"
            case Operation.Delete | Operation.Autoremove:
                return "/usr/sbin/pkg_delete"
            case Operation.Refresh:
                return ""
            case Operation.Search:
                return "/usr/sbin/pkg_info"
            case _:
                raise ValueError(f"Unsupported operation: {op}")

    def pkg_cmd(self, op: Optional[Operation] = None) -> list[str]:
        """Return the path to the package manager."""
        if op is None:
            raise ValueError("Operation is a required argument on OpenBSD.")
        cmd = self._cmd(op)
        if self.sudo is not None:
            return [self.sudo, cmd]
        return [cmd]

    def refresh(self, **kwargs) -> int:
        """Update the local package cache."""
        self.log.info("Refresh is a no-op on OpenBSD.")
        return 0

    def upgrade(self, **kwargs) -> int:
        """Install available updates."""
        cmd = ["-u"]
        _, code = self._run(cmd, op=Operation.Upgrade)
        return code

    def install(self, *args, **kwargs) -> int:
        """Install one or more packages."""
        assert len(args) > 0
        argstr: Final[str] = BLANK.join(args)
        self.log.debug("Install %s",
                       argstr)
        _, code = self._run(list(args), op=Operation.Install)
        return code

    def remove(self, *args, **kwargs) -> int:
        """Remove one or more packages."""
        assert len(args) > 0
        argstr: Final[str] = BLANK.join(args)
        self.log.debug("Uninstall %s",
                       argstr)
        _, code = self._run(list(args), op=Operation.Delete)
        return code

    def autoremove(self, *args, **kwargs) -> int:
        """Remove unneeded packages."""
        self.log.debug("Remove unneeded packages.")
        _, code = self._run(["-a"], op=Operation.Autoremove)
        return code

    def cleanup(self, *args, **kwargs) -> int:
        """Clean up downloaded package files."""
        self.log.debug("Cleanup is not implemented on OpenBSD.")
        return 0

    def audit(self, *args, **kwargs) -> list[Package]:
        """Audit installed packages for known vulnerabilities."""
        # We *could* configure a 3rd-party audit tool like lynis...
        print("Audit on OpenBSD is not implemented, yet.")
        return []

    def search(self, *args, **kwargs) -> list[Package]:
        """Search for available packages."""
        assert len(args) > 0
        argstr: Final[str] = BLANK.join(args)
        self.log.debug("Search for %s", argstr)
        cmd = ["-Q"]
        cmd.extend(args)
        self._run(cmd, True, op=Operation.Search)

        packages: list[Package] = []
        m = openBSDPat.findall(self.output[0])
        if len(m) == 0:
            self.log.error("Cannot parse output of pkg_info:\n%s\n\n%s\n\n\n",
                           self.output[0],
                           self.output[1])
        else:
            for group in m:
                info: str = ""
                if len(group) == 3:
                    info = "i" if group[2] == "installed" else ""

                p: Package = Package(name=group[0],
                                     desc="",
                                     kind="",
                                     info=info,
                                     version=group[1])
                packages.append(p)

        return packages

# Local Variables: #
# python-indent: 4 #
# End: #
