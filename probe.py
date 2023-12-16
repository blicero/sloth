#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-12-16 00:28:38 krylon>
#
# /data/code/python/sloth/probe.py
# created on 14. 12. 2023
# (c) 2023 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
sloth.probe

(c) 2023 Benjamin Walkenhorst

Discover what OS we are running on exactly.
"""

import re
from typing import Final, NamedTuple, Optional

import krylib


class Platform(NamedTuple):
    """Platform identifies a combination of hardware architecture, operating
    system, and version.
    Example: Platform("Debian", "bookworm", "amd64")"""
    name: str
    version: str
    arch: str


os_rel: Final[str] = "/etc/os-release"
rel_pat: Final[re.Pattern] = \
    re.compile("^([^=]+)=(.*)$")
quot_pat: Final[re.Pattern] = re.compile('^"([^"]+)"$')


def unquote(s: Final[str]) -> str:
    """Remove leading and trailing quotation marks from a string."""
    m = quot_pat.find(s)
    if m is None:
        return s
    return m[1]


def guess_os() -> Platform:
    """Attempt to determine which platform we are running on."""
    # First step, we try /etc/os-release, if it exists.
    if krylib.fexist(os_rel):
        info: dict[str, str] = {}
        with open(os_rel, "r") as fh:
            for line in fh:
                m: Optional[re.Match] = rel_pat.search(line)
                if m is not None:
                    key: Final[str] = m[1].lower()
                    val: Final[str] = m[2]
                    info[key] = unquote(val)
        match info["id"]:
            case "debian":
                return Platform("debian", info["version_id"], "unknown")


# Local Variables: #
# python-indent: 4 #
# End: #
