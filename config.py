#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-08 21:37:40 krylon>
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

from tomlkit import TOMLDocument, loads

from sloth import common


class Config:
    """Config deals with the configuration file."""

    __slots__ = [
        "path",
        "log",
    ]

    path: str
    log: logging.Logger
    cfg: TOMLDocument

    def __init__(self, path: str = "") -> None:
        if path == "":
            path = common.path.config()
        self.path = path
        self.log = common.get_logger("config")
        with open(self.path, "r", encoding="utf-8") as fh:
            self.cfg = loads(fh)


# Local Variables: #
# python-indent: 4 #
# End: #
