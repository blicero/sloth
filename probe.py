#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-04 17:44:55 krylon>
#
# /data/code/python/sloth/probe.py
# created on 14. 12. 2023
# (c) 2023 Benjamin Walkenhorst
#
# This file is part of the Sloth Meta Package Manager. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
sloth.probe

(c) 2023 Benjamin Walkenhorst

Discover what OS we are running on exactly.
"""

import re
import subprocess as sp
from shutil import which
from typing import Final, NamedTuple, Optional

import krylib


class Platform(NamedTuple):
    """Platform identifies a combination of hardware architecture, OS, and version.

    Example: Platform("Debian", "bookworm", "amd64")
    """

    name: str
    version: str
    arch: str


OS_REL: Final[str] = "/etc/os-release"
REL_PAT: Final[re.Pattern] = \
    re.compile("^([^=]+)=(.*)$")
QUOT_PAT: Final[re.Pattern] = re.compile('^"([^"]+)"$')


def unquote(s: str) -> str:
    """Remove leading and trailing quotation marks from a string."""
    m = QUOT_PAT.search(s)
    if m is None:
        return s
    return m[1]


def guess_os(osrel: str = OS_REL) -> Platform:
    """Attempt to determine which platform we are running on."""
    # First step, we try /etc/os-release, if it exists.
    if krylib.fexist(osrel):
        info: dict[str, str] = {}
        with open(osrel, "r", encoding="utf-8") as fh:
            for line in fh:
                m: Optional[re.Match] = REL_PAT.search(line)
                if m is not None:
                    key: str = m[1].lower()
                    val: str = m[2]
                    info[key] = unquote(val)
        match info["id"]:
            case "debian":
                return Platform("debian", info["version_id"], "unknown")
            case "raspbian":
                return Platform("debian", info["version_id"], "raspberry-pi")
            case "opensuse-tumbleweed" | "opensuse-leap":
                return Platform(info["id"], info["version_id"], "unknown")
            case "freebsd":
                return Platform("freebsd", info["version_id"], "unknown")
            case "arch" | "manjaro":
                return Platform("arch", info["version_id"], "unknown")

    uname: Final[str] = sp.check_output(["/bin/uname", "-smr"]).decode()
    sysname, version, arch = uname.strip().split()
    return Platform(sysname.lower(), version, arch)


def find_sudo() -> Optional[str]:
    """Find the command to run commands with elevated privileges."""
    # We prefer doas over sudo, because the latter sometimes is very
    # persistent about wanting a password, and I'm kinda lazy.
    commands: Final[list[str]] = ["doas", "sudo", "run0"]
    for c in commands:
        full_path: Optional[str] = which(c)
        if full_path is not None:
            return full_path
    return None

# Local Variables: #
# python-indent: 4 #
# End: #
