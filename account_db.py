# coding: utf-8
# Copyright (c) 2024 Jungheil <jungheilai@gmail.com>
# OBGym is licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.

import base64
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Union

import pytz
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class AccountSQLite:
    """
    SQLite database manager for user accounts
    Handles account storage, updates, and queries
    """

    def __init__(self, db_name: str) -> None:
        """
        Initialize database connection and create tables if needed

        Args:
            db_name: Path to SQLite database file
        """
        self.db_name = db_name

        salt = b"0e1dbefc-f2bd-42f9-b139-d85cf3f6b729"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(b"6663ee1a-8c55-44a3-a2b5-6cbb08b1f3cb")
        )
        self.cipher_suite = Fernet(key)
        self.conn = self.create_connection()
        self.create_table_if_not_exists()

    def create_connection(self) -> sqlite3.Connection:
        """
        Create a database connection

        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_name)
        return conn

    def create_table_if_not_exists(self) -> None:
        """
        Create accounts table if it doesn't exist
        Table schema includes: id, username, password, cookies, valid status, and last update time
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                cookies TEXT,
                valid BOOLEAN DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
        """
        )
        self.conn.commit()

    def add_account(self, username: str, password: str) -> bool:
        """
        Add a new account to the database

        Args:
            username: Account username
            password: Account password

        Returns:
            bool: True if account was added successfully, False if username already exists
        """
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT id FROM accounts WHERE username = ?
        """,
            (username,),
        )
        account = cursor.fetchone()
        if account:
            logging.warning("Account with this username already exists.")
            return False

        encrypted_password = self.cipher_suite.encrypt(password.encode())

        cursor.execute(
            """
            INSERT INTO accounts (username, password)
            VALUES (?, ?)
        """,
            (username, encrypted_password),
        )
        self.conn.commit()

        return True

    def delete_account(self, username: str) -> bool:
        """
        Delete an account from the database

        Args:
            username: Account username to delete

        Returns:
            bool: True if operation was successful
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            DELETE FROM accounts WHERE username = ?
        """,
            (username,),
        )
        self.conn.commit()
        return True

    def set_cookies(self, username: str, cookies: str) -> bool:
        """
        Update account's cookies and last updated timestamp

        Args:
            username: Account username
            cookies: Cookie string to store

        Returns:
            bool: True if operation was successful
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE accounts
            SET cookies = ?, last_updated = CURRENT_TIMESTAMP
            WHERE username = ?
        """,
            (cookies, username),
        )
        self.conn.commit()
        return True

    def set_valid(self, username: str, valid: bool) -> bool:
        """
        Update account's validity status and last updated timestamp

        Args:
            username: Account username
            valid: New validity status

        Returns:
            bool: True if operation was successful
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE accounts
            SET valid = ?, last_updated = CURRENT_TIMESTAMP
            WHERE username = ?
        """,
            (valid, username),
        )
        self.conn.commit()
        return True

    def query_accounts(self, username: Optional[str] = None) -> List[Tuple]:
        """
        Query account information

        Args:
            username: Optional username to filter query

        Returns:
            List of tuples containing account information:
            (id, username, password, cookies, valid, last_updated)
        """
        cursor = self.conn.cursor()
        if username:
            cursor.execute(
                """
                SELECT id, username, password, cookies, valid, last_updated FROM accounts
                WHERE username = ?
            """,
                (username,),
            )
        else:
            cursor.execute(
                """
                SELECT id, username, password, cookies, valid, last_updated FROM accounts
            """
            )
        rows = cursor.fetchall()

        decrypted_rows = []
        for row in rows:
            decrypted_row = list(row)
            decrypted_row[2] = self._decrypt_password(row[2])  # 解密密码字段
            decrypted_rows.append(tuple(decrypted_row))
        return decrypted_rows

    def get_all_accounts(self) -> List[Tuple]:
        """
        Get all accounts from database

        Returns:
            List of tuples containing account information:
            (id, username, password, cookies, valid, last_updated)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, username, password, cookies, valid, last_updated FROM accounts
        """
        )
        rows = cursor.fetchall()

        decrypted_rows = []
        for row in rows:
            decrypted_row = list(row)
            decrypted_row[2] = self._decrypt_password(row[2])
            decrypted_rows.append(tuple(decrypted_row))
        return decrypted_rows

    def get_valid_account(self) -> List[Tuple]:
        """
        Get all valid accounts from database

        Returns:
            List of tuples containing valid account information:
            (id, username, password, cookies, valid, last_updated)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, username, password, cookies, valid, last_updated FROM accounts
            WHERE valid = 1
        """
        )
        rows = cursor.fetchall()

        decrypted_rows = []
        for row in rows:
            decrypted_row = list(row)
            decrypted_row[2] = self._decrypt_password(row[2])
            decrypted_rows.append(tuple(decrypted_row))
        return decrypted_rows

    def get_timeout_account(self, timeout: Union[int, float]) -> List[Tuple]:
        """
        Get accounts that haven't been updated within the timeout period

        Args:
            timeout: Timeout period in hours

        Returns:
            List of tuples containing timed-out account information:
            (id, username, password, cookies, valid, last_updated)
        """
        cursor = self.conn.cursor()
        timeout_time = datetime.now(pytz.utc) - timedelta(hours=timeout)
        timeout_str = timeout_time.strftime("%Y-%m-%d %H:%M:%S")

        query = """
            SELECT id, username, password, cookies, valid, last_updated FROM accounts
            WHERE last_updated < ?
        """
        cursor.execute(query, (timeout_str,))
        rows = cursor.fetchall()

        decrypted_rows = []
        for row in rows:
            decrypted_row = list(row)
            decrypted_row[2] = self._decrypt_password(row[2])
            decrypted_rows.append(tuple(decrypted_row))
        return decrypted_rows

    def close_connection(self) -> None:
        """
        Close the database connection
        """
        self.conn.close()

    def _decrypt_password(self, encrypted_password: bytes) -> str:
        """
        decrypt password

        Args:
            encrypted_password: Encrypted password

        Returns:
            str: Decrypted password
        """
        return self.cipher_suite.decrypt(encrypted_password).decode()
