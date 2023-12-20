#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-12-19 01:06:07 krylon>
#
# /data/code/python/sloth/database.py
# created on 18. 12. 2023
# (c) 2023 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
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
from typing import Final, Optional, Union

import krylib

from pkg import Operation


INIT_QUERIES: Final[list[str]] = [
    """
    CREATE TABLE operation (
        id INTEGER PRIMARY KEY,
        op TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        args TEXT NOT NULL DEFAULT ''
    )
    """,
    "CREATE INDEX idx_op_op ON operation (op)",
    "CREATE INDEX idx_op_time ON operation (timestamp)",
]


class QueryID(Enum):
    """Symbolic constants to identify database queries."""
    OpAdd = auto()
    OpGetRecent = auto()


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
}


# Local Variables: #
# python-indent: 4 #
# End: #
