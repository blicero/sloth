#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-11 16:06:22 krylon>
#
# /data/code/python/sloth/config.py
# created on 08. 04. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the Sloth Meta Package Manager. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
sloth.config

(c) 2025 Benjamin Walkenhorst
"""


import logging
from typing import Final

from krylib import fexist
from tomlkit import TOMLDocument
from tomlkit.toml_file import TOMLFile

from sloth import common

DEFAULT_CONFIG: Final[str] = """# Time-stamp: <2025-04-09 22:02:03 krylon>

[shell]
refresh-interval = 86400
say-yes = true
remove-dependencies = true
nice = true

"""


class Config:
    """Config deals with the configuration file."""

    __slots__ = [
        "path",
        "log",
        "cfg",
        "file",
    ]

    path: str
    log: logging.Logger
    cfg: TOMLDocument
    file: TOMLFile

    def __init__(self, path: str = "") -> None:
        if path == "":
            path = common.path.config()
        self.path = path
        self.log = common.get_logger("config")
        if not fexist(path):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(DEFAULT_CONFIG)
        self.file = TOMLFile(self.path)
        self.cfg = self.file.read()

    def save(self) -> None:
        """Write the configuration state to disk."""
        self.file.write(self.cfg)

# Local Variables: #
# python-indent: 4 #
# End: #
