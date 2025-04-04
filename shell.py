#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-04 17:54:19 krylon>
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
import shlex
from cmd import Cmd
from datetime import datetime

from sloth import common, database, pkg


class Shell(Cmd):
    """Interactive interface to the package manager."""

    __slots__ = [
        "db",
        "log",
        "pk",
        "timestamp",
    ]

    db: database.Database
    log: logging.Logger
    pk: pkg.PackageManager
    timestamp: datetime

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

    def precmd(self, line) -> str:
        """Save the time before executing the command."""
        self.timestamp = datetime.now()
        return line

    def postcmd(self, stop, line) -> bool:
        """After running the command, display how much time it took."""
        after = datetime.now()
        delta = after - self.timestamp
        print(f"Command started at {self.timestamp:%Y-%m-%d %H:%M:%S} and took {delta} to execute")
        return stop

    def do_refresh(self, _arg: str) -> bool:
        """Refresh the package database."""
        self.pk.refresh()
        return False

    def do_search(self, arg: str) -> bool:
        """Search for packages."""
        self.log.debug("Search for %s", arg)
        packages = self.pk.search(*shlex.split(arg))
        for p in packages:
            print(f"{p.info:8} {p.name} - {p.desc}")
        print("")
        return False

    def do_upgrade(self, _arg: str) -> bool:
        """Install pending updates."""
        self.log.debug("Update existing packages.")
        self.pk.upgrade()
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
