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

import asyncio
import functools
import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from dataclasses_json import dataclass_json

from account_db import AccountSQLite
from api.cas_api import CASLogin
from gym import Gym, GymArea


CHINA_TIMEZONE = pytz.timezone("Asia/Shanghai")


class JobStatus(int, Enum):
    PENDING = 0
    RUNNING = 1
    RETRY = 2
    SUCCESS = 3
    FAILED = 4


class JobLevel(int, Enum):
    MAIN = 0
    USER = 1


class JobType(int, Enum):
    UNKNOW = 0
    RENEW = 1
    BOOK = 2


@dataclass_json
@dataclass
class TaskResult:
    success: bool
    message: str
    data: Dict
    created_at: str = field(
        default_factory=lambda: datetime.now(CHINA_TIMEZONE).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


@dataclass_json
@dataclass
class TaskTodo:
    task_id: str
    date: str


@dataclass_json
@dataclass
class Job:
    status: JobStatus
    job_level: JobLevel
    job_id: str
    description: str
    kwargs: Dict
    job_type: JobType = JobType.UNKNOW
    result: List[TaskResult] = field(default_factory=list)
    failed_count: int = 0
    task_todo: Optional[TaskTodo] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(CHINA_TIMEZONE).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(CHINA_TIMEZONE).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


async def _task_update_account(
    username: str, password: str
) -> Dict[str, Dict[str, str]]:
    """
    Update account cookies by performing a new login.

    Args:
        username: Account username
        password: Account password

    Returns:
        Dict containing username and cookies mapping
        Example: {username: {cookie_name: cookie_value}}
    """
    try:
        login = CASLogin()
        response = await login.get(
            username,
            password,
            "https://gym.sysu.edu.cn/app/login/pre.html",
        )
        cookies_dict = {}
        for cookie in response.cookies.jar:
            if cookie.domain == "gym.sysu.edu.cn":
                cookies_dict[cookie.name] = cookie.value
        if len(cookies_dict) == 0:
            raise RuntimeError("Login failed, no cookies found")
        cookies_str = json.dumps(cookies_dict)
        db = AccountSQLite("db/accounts.db")
        db.set_cookies(username, cookies_str)
        db.set_valid(username, True)
        return {username: cookies_dict}
    except Exception as e:
        logging.error("Error updating account %s: %s", username, str(e))
        return {username: {}}


async def _task_update_expired_accounts() -> Dict[str, Dict[str, str]]:
    """
    Update cookies for all expired accounts.

    Returns:
        Dict mapping usernames to their new cookies
        Example: {username1: cookies1, username2: cookies2}
    """
    try:
        db = AccountSQLite("db/accounts.db")
        expired_accounts = db.get_timeout_account(2)
        tasks = [
            _task_update_account(account[1], account[2]) for account in expired_accounts
        ]
        data = await asyncio.gather(*tasks)
        return {k: v for d in data for k, v in d.items()}
    except Exception as e:
        logging.error("Error updating expired accounts: %s", str(e))
        return {}


def task_update_account(username: str, password: str) -> Dict[str, Dict[str, str]]:
    """
    Synchronous wrapper for _task_update_account.

    Args:
        username: Account username
        password: Account password

    Returns:
        Dict containing username and cookies mapping
    """
    return asyncio.run(_task_update_account(username, password))


def task_update_expired_accounts() -> Dict[str, Dict[str, str]]:
    """
    Synchronous wrapper for _task_update_expired_accounts.

    Returns:
        Dict mapping usernames to their new cookies
    """
    return asyncio.run(_task_update_expired_accounts())


def task_book(
    area: Dict[str, Any], username: str, renew_account: bool = False
) -> Dict[str, Any]:
    """
    Book a gym area for a user.

    Args:
        area: Area information dictionary
        username: Account username
        renew_account: Whether to renew account cookies before booking

    Returns:
        Dict containing booking result information

    Raises:
        RuntimeError: If account not found or renewal fails
    """
    area = GymArea.from_dict(area)
    db = AccountSQLite("db/accounts.db")
    account_data = db.query_accounts(username)
    if not account_data:
        raise RuntimeError("Account not found")

    if renew_account:
        cookies = {}
        for i in range(3):
            logging.info("Trying to update account %s, attempt %d", username, i + 1)
            ret = asyncio.run(_task_update_account(username, account_data[0][2]))
            cookies = ret.get(username, {})
            if cookies:
                break
        if not cookies:
            raise RuntimeError("Failed to renew account")
    else:
        cookies_str = account_data[0][3]
        cookies = json.loads(cookies_str)

    gym = Gym()
    ret = asyncio.run(gym.book(area, cookies))
    return ret.to_dict() if ret else {}


class JobSQLite:
    def __init__(self, db_name: str) -> None:
        """
        Initialize JobSQLite database manager.

        Args:
            db_name: Path to SQLite database file
        """
        self.db_name = db_name
        self.conn = self.create_connection()
        self.create_table_if_not_exists()

    def create_connection(self) -> sqlite3.Connection:
        """
        Create a database connection.

        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_name)
        return conn

    def create_table_if_not_exists(self) -> None:
        """
        Create jobs table if it doesn't exist.
        Table schema includes job details and status information.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status INTEGER NOT NULL,
                job_level INTEGER NOT NULL,
                description TEXT NOT NULL,
                kwargs TEXT NOT NULL,
                job_type INTEGER NOT NULL,
                result TEXT NOT NULL,
                failed_count INTEGER NOT NULL,
                task_todo TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def add_job(self, job: Job) -> bool:
        """
        Add a new job to the database.

        Args:
            job: Job object to add

        Returns:
            bool: True if job was added successfully
        """
        cursor = self.conn.cursor()
        try:
            job.updated_at = datetime.now(CHINA_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """
                INSERT INTO jobs (
                    job_id, status, job_level, description, kwargs,
                    job_type, result, failed_count, task_todo, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.status.value,
                    job.job_level.value,
                    job.description,
                    json.dumps(job.kwargs),
                    job.job_type.value,
                    json.dumps([r.to_dict() for r in job.result]),
                    job.failed_count,
                    job.task_todo.to_json() if job.task_todo else None,
                    job.created_at,
                    job.updated_at,
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error adding job: {e}")
            return False

    def update_job(self, job: Job) -> bool:
        """
        Update existing job in the database.

        Args:
            job: Job object with updated information

        Returns:
            bool: True if job was updated successfully
        """
        cursor = self.conn.cursor()
        try:
            job.updated_at = datetime.now(CHINA_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """
                UPDATE jobs SET
                    status = ?,
                    job_level = ?,
                    description = ?,
                    kwargs = ?,
                    job_type = ?,
                    result = ?,
                    failed_count = ?,
                    task_todo = ?,
                    created_at = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (
                    job.status.value,
                    job.job_level.value,
                    job.description,
                    json.dumps(job.kwargs),
                    job.job_type.value,
                    json.dumps([r.to_dict() for r in job.result]),
                    job.failed_count,
                    job.task_todo.to_json() if job.task_todo else None,
                    job.created_at,
                    job.updated_at,
                    job.job_id,
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error updating job: {e}")
            return False

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from the database.

        Args:
            job_id: ID of job to delete

        Returns:
            bool: True if job was deleted successfully
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error deleting job: {e}")
            return False

    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job information by ID.

        Args:
            job_id: Job ID to query

        Returns:
            Job object if found, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        if row:
            return Job(
                status=JobStatus(row[1]),
                job_level=JobLevel(row[2]),
                job_id=row[0],
                description=row[3],
                kwargs=json.loads(row[4]),
                job_type=JobType(row[5]),
                result=[TaskResult.from_dict(r) for r in json.loads(row[6])],
                failed_count=row[7],
                task_todo=TaskTodo.from_json(row[8]) if row[8] else None,
                created_at=row[9],
                updated_at=row[10],
            )
        return None

    def get_all_jobs(
        self,
        job_level: Optional[JobLevel] = None,
        job_type: Optional[JobType] = None,
        status: Optional[JobStatus] = None,
    ) -> Dict[str, Job]:
        """
        Get all jobs matching specified filters.

        Args:
            job_level: Filter by job level
            job_type: Filter by job type
            status: Filter by job status

        Returns:
            Dict mapping job IDs to Job objects
        """
        cursor = self.conn.cursor()
        if job_level is not None or job_type is not None or status is not None:
            conditions = []
            values = []

            if job_level is not None:
                conditions.append("job_level = ?")
                values.append(job_level.value)
            if job_type is not None:
                conditions.append("job_type = ?")
                values.append(job_type.value)
            if status is not None:
                conditions.append("status = ?")
                values.append(status.value)
            cursor.execute(
                "SELECT * FROM jobs WHERE " + " AND ".join(conditions), tuple(values)
            )
        else:
            cursor.execute("SELECT * FROM jobs")
        rows = cursor.fetchall()
        return {
            row[0]: Job(
                status=JobStatus(row[1]),
                job_level=JobLevel(row[2]),
                job_id=row[0],
                description=row[3],
                kwargs=json.loads(row[4]),
                job_type=JobType(row[5]),
                result=[TaskResult.from_dict(r) for r in json.loads(row[6])],
                failed_count=row[7],
                task_todo=TaskTodo.from_json(row[8]) if row[8] else None,
                created_at=row[9],
                updated_at=row[10],
            )
            for row in rows
        }

    def get_running_jobs(self) -> Dict[str, Job]:
        """
        Get all currently running jobs.

        Returns:
            Dict mapping job IDs to Job objects
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM jobs WHERE status = ?", (JobStatus.RUNNING.value,)
        )
        rows = cursor.fetchall()
        return {
            row[0]: Job(
                status=JobStatus(row[1]),
                job_level=JobLevel(row[2]),
                job_id=row[0],
                description=row[3],
                kwargs=json.loads(row[4]),
                job_type=JobType(row[5]),
                result=[TaskResult.from_dict(r) for r in json.loads(row[6])],
                failed_count=row[7],
                task_todo=TaskTodo.from_json(row[8]) if row[8] else None,
                created_at=row[9],
                updated_at=row[10],
            )
            for row in rows
        }

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()


class JobManager:
    def __init__(self) -> None:
        """
        Initialize JobManager with scheduler and job database.
        Sets up scheduler and resumes existing jobs.
        """
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.job_db_path = "db/jobs.db"
        self.not_execute_time = [(time(22, 0, 0, 0), time(23, 59, 59, 999999))]
        self._resume()

    def __del__(self):
        self.scheduler.shutdown()

    # 恢复任务
    def _resume(self) -> None:
        """Resume all existing jobs from database."""
        self.remove_all_main_jobs()
        self._resume_book_job()

    def _resume_book_job(self) -> None:
        """Resume existing booking jobs from database."""
        job_db = JobSQLite(self.job_db_path)
        jobs = job_db.get_all_jobs(job_type=JobType.BOOK, status=JobStatus.RUNNING)

        for job in jobs.values():
            if job.task_todo is not None:
                task_func = self.task_wrapper(
                    task_book, self._job_only_book_hook(job.job_id), job.kwargs
                )
                self.scheduler.add_job(
                    task_func,
                    "date",
                    run_date=job.task_todo.date,
                    timezone=CHINA_TIMEZONE,
                    id=job.task_todo.task_id,
                )
        jobs = job_db.get_all_jobs(job_type=JobType.BOOK, status=JobStatus.RETRY)
        for job in jobs.values():
            job.status = JobStatus.FAILED
            job.task_todo = None
            job_db.update_job(job)

    def remove_job(self, job_id: str) -> None:
        """
        Remove a job and its scheduled tasks.

        Args:
            job_id: ID of job to remove

        Raises:
            RuntimeError: If job not found
        """
        job_db = JobSQLite(self.job_db_path)
        job = job_db.get_job(job_id)
        if not job:
            raise RuntimeError("Job not found")
        if job.task_todo is not None:
            self.scheduler.remove_job(job.task_todo.task_id)
        job_db.delete_job(job_id)

    def remove_user_job(self, job_id: str) -> None:
        """
        Remove a user-level job.

        Args:
            job_id: ID of job to remove

        Raises:
            RuntimeError: If job not found or not a user job
        """
        job_db = JobSQLite(self.job_db_path)
        job = job_db.get_job(job_id)
        if not job:
            raise RuntimeError("Job not found")
        if job.job_level != JobLevel.USER:
            raise RuntimeError("Job is not a user job")
        if job.task_todo is not None:
            try:
                self.scheduler.remove_job(job.task_todo.task_id)
            except Exception as e:
                pass
        job_db.delete_job(job_id)

    def remove_all_main_jobs(self) -> None:
        """Remove all main-level jobs from database."""
        job_db = JobSQLite(self.job_db_path)
        jobs = job_db.get_all_jobs(job_level=JobLevel.MAIN)
        for job in jobs.values():
            job_db.delete_job(job.job_id)

    def job_only_book(
        self, area: GymArea, username: str, renew_account: bool = True
    ) -> str:
        """
        Create a single booking job.

        Args:
            area: GymArea object with booking details
            username: Account username
            renew_account: Whether to renew account before booking

        Returns:
            str: ID of created job

        Raises:
            RuntimeError: If booking date is invalid
        """
        job_db = JobSQLite(self.job_db_path)
        job_id = str(uuid.uuid4())
        kwargs = {
            "area": area.to_dict(),
            "username": username,
            "renew_account": renew_account,
        }
        description = f"book {area.sname} {area.sdate} {area.timeno}"
        job = Job(
            JobStatus.RUNNING,
            JobLevel.USER,
            job_id,
            description,
            kwargs,
            job_type=JobType.BOOK,
        )

        task_func = self.task_wrapper(
            task_book, self._job_only_book_hook(job_id), kwargs
        )
        sdate = (
            datetime.strptime(area.sdate, "%Y-%m-%d")
            .replace(tzinfo=CHINA_TIMEZONE)
            .date()
        )
        today = datetime.now(CHINA_TIMEZONE).date()
        if sdate < today:
            raise RuntimeError("Invalid sdate")
        if sdate > today + timedelta(days=1):
            run_date = datetime.strptime(area.sdate, "%Y-%m-%d").replace(
                tzinfo=CHINA_TIMEZONE
            ) + timedelta(seconds=3)
        else:
            run_date = datetime.now(CHINA_TIMEZONE) + timedelta(seconds=3)
        task_id = str(uuid.uuid4())

        job.task_todo = TaskTodo(
            task_id,
            run_date.strftime("%Y-%m-%d %H:%M:%S"),
        )

        self.scheduler.add_job(
            task_func,
            "date",
            run_date=run_date,
            timezone=CHINA_TIMEZONE,
            id=task_id,
        )
        job_db.add_job(job)
        return job_id

    def _job_only_book_hook(self, job_id: str) -> Callable[[TaskResult], str]:
        """
        Create hook function for booking job.

        Args:
            job_id: ID of associated job

        Returns:
            Callable that processes booking result and updates job status
        """

        def hook(result):
            job_db = JobSQLite(self.job_db_path)

            job = job_db.get_job(job_id)
            if not job:
                return

            job.result.append(result)
            job.task_todo = None

            time_str = job.kwargs["area"]["timeno"].strip().split("-")[1]
            date_str = job.kwargs["area"]["sdate"]
            end_time = datetime.strptime(
                f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=CHINA_TIMEZONE)

            if end_time < datetime.now(CHINA_TIMEZONE):
                job.status = JobStatus.SUCCESS
                job_db.update_job(job)
                return job_id

            task_func = self.task_wrapper(
                task_book,
                self._job_only_book_hook(job_id),
                job.kwargs,
            )

            if result.success:
                job.failed_count = 0
                job.status = JobStatus.RUNNING
                run_date = datetime.now(CHINA_TIMEZONE) + timedelta(minutes=30)
                task_id = str(uuid.uuid4())
                job.task_todo = TaskTodo(
                    task_id,
                    run_date.strftime("%Y-%m-%d %H:%M:%S"),
                )
                self.scheduler.add_job(
                    task_func,
                    "date",
                    run_date=run_date,
                    timezone=CHINA_TIMEZONE,
                    id=task_id,
                )
                job_db.update_job(job)
            else:
                if job.failed_count >= 2:
                    job.failed_count += 1
                    job.status = JobStatus.FAILED
                    job_db.update_job(job)
                else:
                    job.status = JobStatus.RETRY
                    job.failed_count += 1
                    run_date = datetime.now(CHINA_TIMEZONE) + timedelta(seconds=20)
                    task_id = str(uuid.uuid4())
                    job.task_todo = TaskTodo(
                        task_id,
                        run_date.strftime("%Y-%m-%d %H:%M:%S"),
                    )
                    self.scheduler.add_job(
                        task_func,
                        "date",
                        run_date=run_date,
                        timezone=CHINA_TIMEZONE,
                        id=task_id,
                    )
                    job_db.update_job(job)
            return job_id

        return hook

    def job_renew_account(self) -> str:
        """
        Create account renewal job.

        Returns:
            str: ID of created job
        """
        job_db = JobSQLite(self.job_db_path)
        job_id = str(uuid.uuid4())
        job = Job(
            JobStatus.RUNNING,
            JobLevel.MAIN,
            job_id,
            "renew account",
            {},
            job_type=JobType.RENEW,
        )

        task_func = self.task_wrapper(
            task_update_expired_accounts, self._job_renew_account_hook(job_id), {}
        )
        run_date = datetime.now(CHINA_TIMEZONE) + timedelta(seconds=3)
        task_id = str(uuid.uuid4())

        job.task_todo = TaskTodo(
            task_id,
            run_date.strftime("%Y-%m-%d %H:%M:%S"),
        )

        self.scheduler.add_job(
            task_func,
            "date",
            run_date=run_date,
            timezone=CHINA_TIMEZONE,
            id=task_id,
        )
        job_db.add_job(job)

        return job_id

    def _job_renew_account_hook(self, job_id: str) -> Callable[[TaskResult], None]:
        """
        Create hook function for account renewal job.

        Args:
            job_id: ID of associated job

        Returns:
            Callable that processes renewal result and schedules next renewal
        """

        def hook(result):
            job_db = JobSQLite(self.job_db_path)

            job_db = JobSQLite("db/jobs.db")
            job = job_db.get_job(job_id)
            if not job:
                return

            job.result.append(result)
            job.task_todo = None

            task_func = self.task_wrapper(
                task_update_expired_accounts, self._job_renew_account_hook(job_id), {}
            )

            if result.success:
                next_date = datetime.now(CHINA_TIMEZONE) + timedelta(hours=2)
                task_id = str(uuid.uuid4())
                job.task_todo = TaskTodo(
                    task_id,
                    next_date.strftime("%Y-%m-%d %H:%M:%S"),
                )
                self.scheduler.add_job(
                    task_func,
                    "date",
                    run_date=next_date,
                    timezone=CHINA_TIMEZONE,
                    id=task_id,
                )
                job_db.update_job(job)

            else:
                next_date = datetime.now(CHINA_TIMEZONE) + timedelta(minutes=30)
                task_id = str(uuid.uuid4())
                job.task_todo = TaskTodo(
                    task_id,
                    next_date.strftime("%Y-%m-%d %H:%M:%S"),
                )
                self.scheduler.add_job(
                    task_func,
                    "date",
                    run_date=next_date,
                    timezone=CHINA_TIMEZONE,
                    id=task_id,
                )
                job_db.update_job(job)

        return hook

    def task_wrapper(
        self,
        func: Callable[..., Any],
        hook_func: Callable[[TaskResult], Any],
        kwargs: Dict[str, Any],
    ) -> Callable[[], TaskResult]:
        """
        Wrap task function with logging and error handling.

        Args:
            func: Task function to wrap
            hook_func: Hook function to call after task completion
            kwargs: Arguments to pass to task function

        Returns:
            Wrapped function that executes task and processes result
        """

        @functools.wraps(func)
        def wrapper():
            now = datetime.now(CHINA_TIMEZONE)
            for start, end in self.not_execute_time:
                if start <= now.time() <= end:
                    logging.info("Task %s not executed at %s", func.__name__, now)
                    return
            logging.info("Task %s started with kwargs: %s", func.__name__, kwargs)
            try:
                data = func(**kwargs)
                ret = TaskResult(True, "", data)
                logging.info("Task %s executed successfully: %s", func.__name__, data)
            except Exception as e:
                logging.error("Task %s failed: %s", func.__name__, str(e))
                ret = TaskResult(False, f"Task {func.__name__} failed: {str(e)}", {})
            hook_func(ret)
            return ret

        return wrapper

    @property
    def jobs(self) -> Dict[str, Job]:
        """
        Get all jobs from database.

        Returns:
            Dict mapping job IDs to Job objects
        """
        job_db = JobSQLite(self.job_db_path)
        return job_db.get_all_jobs()
