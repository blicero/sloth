#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-07 21:29:14 krylon>
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
import html
import logging
import readline
import shlex
from cmd import Cmd
from datetime import datetime

from prompt_toolkit import HTML
from prompt_toolkit.shortcuts import checkboxlist_dialog

from sloth import common, database, pkg
from sloth.pkg import Operation, Package


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
        with self.db:
            self.pk.refresh()
            self.db.op_add(Operation.Refresh, "", 0)
        return False

    def do_search(self, arg: str) -> bool:
        """Search for packages."""
        self.log.debug("Search for %s", arg)
        packages = self.pk.search(*shlex.split(arg))
        if len(packages) > 0:
            dlg = checkboxlist_dialog(
                title="Results",
                text=f"{len(packages)} Search results for '{arg}'",
                values=[(x, pkg_fancy(x)) for x in packages],
                default_values=[x for x in packages if x.info],
            )

            results = dlg.run()
            if results:
                print([p.name for p in results])
        return False

    def do_upgrade(self, _arg: str) -> bool:
        """Install pending updates."""
        self.log.debug("Update existing packages.")
        with self.db:
            self.pk.upgrade()
            self.db.op_add(Operation.Upgrade, "", 0)
        return False

    def do_install(self, arg: str) -> bool:
        """Install one or more package(s)."""
        self.log.info("About to install %s", arg)
        packages = self.pk.search(*shlex.split(arg))
        if len(packages) == 0:
            return False
        with self.db:
            self.pk.install(*packages)
            self.db.op_add(Operation.Install, arg, 0)
            return False

    def do_remove(self, arg: str) -> bool:
        """Remove package(s)."""
        self.log.info("About to remove %s", arg)
        packages = shlex.split(arg)
        if len(packages) == 0:
            return False
        print("Uninstall is not implemented, yet.")
        return False

    def do_EOF(self, _) -> bool:
        """Handle EOF (by quitting)."""
        print("")
        self.log.info("Bye bye")
        return True


def pkg_fancy(p: Package) -> HTML:
    """Return a nicely formatted version of the package's name and description"""
    name: str = p.name
    if p.version:
        name += f"-{p.version}"
    s = f"<b>{html.escape(name)}</b> - <u>{html.escape(p.desc)}</u>"
    return HTML(s)


if __name__ == '__main__':
    sh = Shell()
    sh.cmdloop()

# Local Variables: #
# python-indent: 4 #
# End: #
