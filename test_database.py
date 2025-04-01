#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-01 15:06:47 krylon>
#
# /data/code/python/sloth/test_database.py
# created on 20. 12. 2023
# (c) 2023 Benjamin Walkenhorst
#
# This file is part of the Sloth Meta Package Manager. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
sloth.test_database

(c) 2023 Benjamin Walkenhorst
"""


import os
import unittest
from datetime import datetime
from typing import Optional

from sloth import common, database
from sloth.pkg import Operation

TEST_DIR: str = os.path.join(
    datetime.now().strftime("sloth_test_database_%Y%m%d_%H%M%S"))


class DatabaseTest(unittest.TestCase):
    """Test the database. Badum Ts!"""

    conn: Optional[database.Database] = None

    @classmethod
    def setUpClass(cls) -> None:  # noqa: D102
        root: str = "/tmp"
        if os.path.isdir("/data/ram"):
            root = "/data/ram"
        global TEST_DIR  # pylint: disable-msg=W0603
        TEST_DIR = os.path.join(
            root,
            datetime.now().strftime("sloth_test_database_%Y%m%d_%H%M%S"))
        common.set_basedir(TEST_DIR)

    @classmethod
    def tearDownClass(cls) -> None:  # noqa: D102
        os.system(f'rm -rf "{TEST_DIR}"')

    @classmethod
    def db(cls, db: Optional[database.Database] = None) -> database.Database:
        """Set or return the database connection."""
        if db is not None:
            cls.conn = db
        if cls.conn is not None:
            return cls.conn
        raise ValueError("conn is None")

    def test_01_db_open(self) -> None:
        """Open the database."""
        db: database.Database = database.Database(common.path.db())
        self.assertIsNotNone(db)
        DatabaseTest.db(db)

    def test_02_db_add(self) -> None:
        """Try adding some records."""
        db = DatabaseTest.db()
        with db:
            for op in Operation:
                op_id = db.op_add(op, "a b c")
                self.assertNotEqual(op_id, 0)

    def test_03_db_op_get(self) -> None:
        db = DatabaseTest.db()
        with db:
            ops = db.op_get_recent()
            self.assertIsNotNone(ops)
            self.assertIsInstance(ops, list)
            self.assertEqual(len(ops), len(Operation))

# Local Variables: #
# python-indent: 4 #
# End: #
