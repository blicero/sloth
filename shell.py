#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-02 10:56:17 krylon>
#
# /data/code/python/sloth/shell.py
# created on 01. 04. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the Sloth Meta Package Manager. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
sloth.shell

(c) 2025 Benjamin Walkenhorst
"""

import atexit
import logging
import readline
from cmd import Cmd

from sloth import common, database, pkg


class Shell(Cmd):
    """Interactive interface to the package manager."""

    __slots__ = [
        "db",
        "log",
        "pk",
    ]

    db: database.Database
    log: logging.Logger
    pk: pkg.PackageManager

    def __init__(self) -> None:
        super().__init__()
        self.log = common.get_logger("Shell")
        self.db = database.Database()
        self.pk = pkg.PackageManager.create()
        self.prompt = f"({self.pk.platform.name} {self.pk.platform.version})>>> "
        try:
            readline.read_history_file(common.path.histfile())
            readline.set_history_length(2000)
        except FileNotFoundError:
            pass
        finally:
            atexit.register(readline.write_history_file, common.path.histfile())

    def do_refresh(self, _arg: str) -> bool:
        """Refresh the package database."""
        self.pk.refresh()
        return False

    def do_search(self, arg: str) -> bool:
        """Search for packages."""
        self.log.debug("Search for %s", arg)
        return False

    def do_EOF(self, _) -> bool:
        """Handle EOF (by quitting)."""
        print("")
        self.log.info("Bye bye")
        return True


if __name__ == '__main__':
    sh = Shell()
    sh.cmdloop()

# Local Variables: #
# python-indent: 4 #
# End: #
