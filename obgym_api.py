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

import json
import socket
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from dataclasses_json import dataclass_json


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
class GymCampus:
    name: str
    code: str


@dataclass_json
@dataclass
class GymFacility:
    name: str
    serviceid: str


@dataclass_json
@dataclass
class GymArea:
    sname: str
    sdate: str
    timeno: str
    serviceid: str
    areaid: str
    stockid: str


@dataclass_json
@dataclass
class GymOrder:
    orderid: str
    createdate: str


@dataclass_json
@dataclass
class TaskTodo:
    task_id: str
    date: str


@dataclass_json
@dataclass
class TaskResult:
    success: bool
    message: str
    data: dict
    created_at: str


@dataclass_json
@dataclass
class Job:
    status: JobStatus
    job_level: JobLevel
    job_id: str
    description: str
    kwargs: Dict
    job_type: JobType
    result: List[TaskResult]
    failed_count: int
    created_at: str
    updated_at: str
    task_todo: Optional[TaskTodo] = None


class OBGymAPI:
    """
    Gym API Client SDK
    Used to call various Gym service interfaces through socket connection
    """

    def __init__(self, host: str = "localhost", port: int = 16999):
        self._host = host
        self._port = port

    def _send_request(self, action: str, kwargs: Dict[str, Any]) -> Dict:
        """
        Send request to server

        Args:
            action: Action name
            kwargs: Request parameters

        Returns:
            Dict: Server response

        Raises:
            RuntimeError: When server returns error status
            ConnectionError: When connection to server fails
        """
        request = {"action": action, "kwargs": kwargs}

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self._host, self._port))
                s.sendall(json.dumps(request).encode("utf-8"))
                response = s.recv(65536).decode("utf-8")
                result = json.loads(response)

                if result["status"] != 0:
                    raise RuntimeError(result.get("message", "Unknown error"))

                return result

        except (socket.error, ConnectionError) as e:
            raise ConnectionError(f"Failed to connect to server: {str(e)}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to decode server response: {str(e)}")

    def add_account(self, account: str, password: str) -> Dict:
        """
        Add a new account

        Args:
            account: Account username
            password: Account password

        Returns:
            Dict: Response data field

        Raises:
            RuntimeError: When adding account fails
        """
        response = self._send_request(
            "add_account", {"account": account, "password": password}
        )
        return response["data"]

    def remove_account(self, account: str) -> Dict:
        """
        Remove an account

        Args:
            account: Account username

        Returns:
            Dict: Response data field

        Raises:
            RuntimeError: When removing account fails
        """
        response = self._send_request("remove_account", {"account": account})
        return response["data"]

    def get_accounts(self) -> List[Dict]:
        """
        Get all accounts

        Returns:
            List[Dict]: List of accounts

        Raises:
            RuntimeError: When getting account list fails
        """
        response = self._send_request("get_accounts", {})
        return response["data"]

    def get_campus(self, account: str) -> List[GymCampus]:
        """
        Get list of campuses

        Args:
            account: Account username

        Returns:
            List[GymCampus]: List of campus objects

        Raises:
            RuntimeError: When getting campus list fails
        """
        response = self._send_request("get_campus", {"account": account})
        try:
            ret = [GymCampus.from_dict(data) for data in response["data"]["GymCampus"]]
        except Exception as e:
            raise RuntimeError(f"Failed to get campus list: {str(e)}")
        return ret

    def get_facility(self, campus: GymCampus, account: str) -> List[GymFacility]:
        """
        Get list of facilities

        Args:
            account: Account username
            campus: Campus object

        Returns:
            List[GymFacility]: List of facility objects

        Raises:
            RuntimeError: When getting facility list fails
        """
        response = self._send_request(
            "get_facility", {"account": account, "campus": campus.to_dict()}
        )
        try:
            ret = [
                GymFacility.from_dict(data) for data in response["data"]["GymFacility"]
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to get facility list: {str(e)}")
        return ret

    def get_area(self, facility: GymFacility, date: str, account: str) -> List[GymArea]:
        """
        Get list of areas

        Args:
            account: Account username
            facility: Facility object
            date: Date string

        Returns:
            List[GymArea]: List of area objects

        Raises:
            RuntimeError: When getting area list fails
        """
        response = self._send_request(
            "get_area",
            {"account": account, "facility": facility.to_dict(), "date": date},
        )
        try:
            ret = [GymArea.from_dict(data) for data in response["data"]["GymArea"]]
        except Exception as e:
            raise RuntimeError(f"Failed to get area list: {str(e)}")
        return ret

    def renew_account(self, account: str) -> Dict:
        """
        Renew account login status

        Args:
            account: Account username

        Returns:
            Dict: Response data field

        Raises:
            RuntimeError: When renewing account fails
        """
        response = self._send_request("renew_account", {"account": account})
        return response["data"]

    def get_all_jobs(self) -> Dict:
        """
        Get list of user jobs

        Returns:
            Dict: Response data containing list of user jobs

        Raises:
            RuntimeError: When getting job list fails
        """
        response = self._send_request("get_all_jobs", {})
        return response["data"]

    def only_book(self, area: GymArea, account: str) -> Dict:
        """
        Create a single booking task

        Args:
            area: Area object
            account: Account username

        Returns:
            Dict: Response data field containing job_id

        Raises:
            RuntimeError: When creating task fails
        """
        response = self._send_request(
            "only_book",
            {
                "area": area.to_dict(),
                "account": account,
            },
        )
        return response["data"]

    def get_job_info(self, job_id: str) -> Job:
        """
        Get detailed job information

        Args:
            job_id: Job ID

        Returns:
            Job: Detailed job information object

        Raises:
            RuntimeError: When getting job information fails
        """
        response = self._send_request("get_job_info", {"job_id": job_id})
        job_data = response["data"]["job"]

        # Convert task result list
        results = []
        for result in job_data["result"]:
            results.append(
                TaskResult(
                    success=result["success"],
                    message=result["message"],
                    data=result["data"],
                    created_at=result["created_at"],
                )
            )

        task_todo = None
        if job_data.get("task_todo"):
            task_todo = TaskTodo(
                task_id=job_data["task_todo"]["task_id"],
                date=job_data["task_todo"]["date"],
            )

        return Job(
            status=JobStatus(job_data["status"]),
            job_level=JobLevel(job_data["job_level"]),
            job_id=job_data["job_id"],
            description=job_data["description"],
            job_type=JobType(job_data["job_type"]),
            result=results,
            failed_count=job_data["failed_count"],
            created_at=job_data["created_at"],
            task_todo=task_todo,
            kwargs=job_data["kwargs"],
            updated_at=job_data["updated_at"],
        )

    def remove_job(self, job_id: str) -> Dict:
        """
        Remove specified job

        Args:
            job_id: Job ID

        Returns:
            Dict: Response data field

        Raises:
            RuntimeError: When removing job fails
        """
        response = self._send_request("remove_job", {"job_id": job_id})
        return response["data"]
