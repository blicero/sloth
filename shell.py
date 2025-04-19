#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-19 22:15:57 krylon>
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
from datetime import datetime, timedelta

from prompt_toolkit import HTML
from prompt_toolkit.shortcuts import checkboxlist_dialog, confirm

from sloth import common, database, pkg
from sloth.config import Config
from sloth.pkg import Operation, Package
from sloth.common import BLANK


class Shell(Cmd):
    """Interactive interface to the package manager."""

    __slots__ = [
        "db",
        "log",
        "pk",
        "timestamp",
        "refresh_interval",
        "auto_yes",
        "remove_deps",
    ]

    db: database.Database
    log: logging.Logger
    pk: pkg.PackageManager
    timestamp: datetime
    refresh_interval: timedelta
    auto_yes: bool
    remove_deps: bool

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
        self.__process_config()

    def __process_config(self):
        cfg = Config()
        self.refresh_interval = timedelta(seconds=cfg.cfg["shell"]["refresh-interval"])
        self.auto_yes = cfg.cfg["shell"]["say-yes"]
        self.remove_deps = cfg.cfg["shell"]["remove-dependencies"]

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

    def refresh_due(self) -> bool:
        """Return true if a refresh of the local package cache is due."""
        op = self.db.op_get_most_recent(Operation.Refresh)
        if op is None:
            return True
        delta = datetime.now() - op["timestamp"]
        return delta > self.refresh_interval

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
            installed: set[Package] = {x for x in packages if x.info}
            dlg = checkboxlist_dialog(
                title="Results",
                text=f"{len(packages)} Search results for '{arg}'",
                values=[(x, pkg_fancy(x)) for x in packages],
                default_values=[x for x in packages if x.info],
            )

            results = dlg.run()
            if not results:
                return False

            with self.db:
                to_install = [r for r in results if r not in installed]
                if len(to_install) > 0:
                    names = BLANK.join([x.name for x in to_install])
                    self.pk.install(*to_install)
                    self.db.op_add(Operation.Install, names, 0)

                to_delete = [r for r in installed if r not in results]
                if len(to_delete) > 0:
                    names = BLANK.join([x.name for x in to_delete])
                    self.pk.remove(*[x.name for x in to_delete])
        else:
            print("No results were found.")

        return False

    def do_upgrade(self, arg: str) -> bool:
        """Install pending updates."""
        self.log.debug("Update existing packages.")
        args = shlex.split(arg)
        with self.db:
            if ("-r" in args) or \
               (self.refresh_due() and confirm("Refresh package cache?")):
                self.pk.refresh()
                self.db.op_add(Operation.Refresh, "", 0)
            self.pk.upgrade()
            self.db.op_add(Operation.Upgrade, arg, 0)
        return False

    def do_install(self, arg: str) -> bool:
        """Install one or more package(s)."""
        self.log.info("About to install %s", arg)
        packages = shlex.split(arg)
        if len(packages) == 0:
            return False
        with self.db:
            if self.refresh_due() and confirm("Refresh package cache?"):
                self.pk.refresh()
                self.db.op_add(Operation.Refresh, "", 0)
            self.pk.install(*packages)
            self.db.op_add(Operation.Install, arg, 0)
            return False

    def do_remove(self, arg: str) -> bool:
        """Remove package(s)."""
        self.log.info("About to remove %s", arg)
        packages = shlex.split(arg)
        if len(packages) == 0:
            return False
        with self.db:
            self.pk.remove(packages)
            self.db.op_add(Operation.Delete, arg, 0)
        return False

    def do_autoremove(self, _arg: str) -> bool:
        """Remove unneeded packages."""
        self.log.info("Remove unneeded packages.")
        with self.db:
            self.pk.autoremove()
            self.db.op_add(Operation.Autoremove, "", 0)
        return False

    def do_clean(self, _arg: str) -> bool:
        """Clean the package cache."""
        self.log.info("Clean local package cache.")
        with self.db:
            self.pk.cleanup()
            self.db.op_add(Operation.Cleanup, "", 0)
        return False

    def do_audit(self, _arg: str) -> bool:
        """Audit installed packages for known vulnerabilities. Not supported on all platforms."""
        self.log.info("Perform audit")
        with self.db:
            self.pk.audit()
            self.db.op_add(Operation.Audit, "", 0)
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
    intro: str = f"{common.APP_NAME} {common.APP_VERSION} (c) 2025 Benjamin Walkenhorst"
    sh = Shell()
    sh.cmdloop(intro)

# Local Variables: #
# python-indent: 4 #
# End: #
