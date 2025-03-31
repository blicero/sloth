#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-03-31 23:00:40 krylon>
#
# /data/code/python/sloth/database.py
# created on 18. 12. 2023
# (c) 2023 Benjamin Walkenhorst
#
# This file is part of the Sloth Meta Package Manager. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
sloth.database

(c) 2023 Benjamin Walkenhorst
"""

import logging
import sqlite3
import threading
import time
from datetime import datetime
from enum import Enum, auto
from typing import Any, Final, Optional

import krylib

from sloth import common
from sloth.pkg import Operation

OPEN_LOCK: Final[threading.Lock] = threading.Lock()

INIT_QUERIES: Final[list[str]] = [
    """
    CREATE TABLE operation (
        id INTEGER PRIMARY KEY,
        op INTEGER NOT NULL,
        timestamp INTEGER NOT NULL,
        args TEXT NOT NULL DEFAULT ''
    ) STRICT
    """,
    "CREATE INDEX idx_op_op ON operation (op)",
    "CREATE INDEX idx_op_time ON operation (timestamp)",
]


# pylint: disable-msg=C0103
class QueryID(Enum):
    """Symbolic constants to identify database queries."""
    OpAdd = auto()
    OpGetRecent = auto()
    OpGetMostRecent = auto()


db_queries: Final[dict[QueryID, str]] = {
    QueryID.OpAdd: """
    INSERT INTO operation (op, timestamp, args)
                   VALUES ( ?,         ?,    ?)
    RETURNING id
    """,
    QueryID.OpGetRecent: """
    SELECT
        id,
        op,
        timestamp,
        args
    FROM operation
    ORDER BY timestamp DESC
    LIMIT ?
    """,
    QueryID.OpGetMostRecent: """
    SELECT
        id,
        timestamp,
        args
    FROM operation
    WHERE op = ?
    ORDER BY timestamp DESC
    LIMIT 1
    """,
}


class Database:
    """Wrapper around the database connection that provides the
    operations we need."""

    __slots__ = [
        "db",
        "log",
        "path",
    ]

    db: sqlite3.Connection
    log: logging.Logger
    path: Final[str]

    def __init__(self, path: str) -> None:
        self.path = path
        self.log = common.get_logger("database")
        self.log.debug("Open database at %s", path)
        with OPEN_LOCK:
            exist: bool = krylib.fexist(path)
            self.db = sqlite3.connect(path)  # pylint: disable-msg=C0103
            self.db.isolation_level = None

            cur: sqlite3.Cursor = self.db.cursor()
            cur.execute("PRAGMA foreign_keys = true")
            cur.execute("PRAGMA journal_mode = WAL")

            if not exist:
                self.__create_db()

    def __create_db(self) -> None:
        """Initialize a freshly created database"""
        with self.db:
            for query in INIT_QUERIES:
                cur: sqlite3.Cursor = self.db.cursor()
                cur.execute(query)

    def __enter__(self) -> None:
        self.db.__enter__()

    def __exit__(self, ex_type, ex_val, traceback):
        return self.db.__exit__(ex_type, ex_val, traceback)

    def op_add(self, op: Operation, args: str) -> int:
        """Log an operation performed to the database."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.OpAdd],
                    (op.value, int(time.time()), args))
        row = cur.fetchone()
        return row[0]

    def op_get_recent(self, limit: int = -1) -> list[Any]:
        """Fetch the <limit> most recent recorded operations
        from the database."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.OpGetRecent], (limit, ))
        operations = []
        for row in cur:
            op = {
                "id": row[0],
                "op": Operation(row[1]),
                "timestamp": datetime.fromtimestamp(row[2]),
                "args": row[3],
            }
            operations.append(op)
        return operations

    def op_get_most_recent(self, op: Operation) -> Optional[dict]:
        """Get the most recent instance of the given Operation."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.OpGetMostRecent], (op, ))
        row = cur.fetchone()
        if row is not None:
            return {
                "id": row[0],
                "op": op,
                "timestamp": datetime.fromtimestamp(row[1]),
                "args": row[2],
            }
        return None

# Local Variables: #
# python-indent: 4 #
# End: #
