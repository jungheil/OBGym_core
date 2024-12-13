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
import json
import logging
import os
import re
import socket
from typing import Dict, Optional

from account_db import AccountSQLite
from api.cas_api import CASLogin
from gym import Gym, GymArea, GymCampus, GymFacility
from job_manager import JobManager

os.makedirs("log", exist_ok=True)

BLUE_COLOR = "\033[94m"
GREEN_COLOR = "\033[92m"
YELLOW_COLOR = "\033[93m"
RED_COLOR = "\033[91m"
PURPLE_COLOR = "\033[95m"
END_COLOR = "\033[0m"
HIGH_INTENSITY = "\033[1m"

LOG_COLORS = {
    "DEBUG": BLUE_COLOR,
    "INFO": GREEN_COLOR,
    "WARNING": YELLOW_COLOR,
    "ERROR": RED_COLOR,
    "CRITICAL": PURPLE_COLOR,
}

LOG_FORMAT = (
    f"{HIGH_INTENSITY}%(color)s%(levelname)s{END_COLOR}:\t"
    f"%(asctime)s "
    f"{HIGH_INTENSITY}[%(filename)s:%(lineno)d]{END_COLOR} "
    f"- %(color)s%(message)s{END_COLOR}"
)


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        record.color = LOG_COLORS.get(record.levelname, END_COLOR)
        return super().format(record)


class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        pattern = r"""
            (["']password["']:\s?["'])(\w*)(["'])
            """
        record.msg = re.sub(
            pattern,
            r"\1***\3",
            record.msg,
            flags=re.VERBOSE,
        )
        return True


handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter(LOG_FORMAT))
handler.addFilter(SensitiveDataFilter())
logging.root.addHandler(handler)

headler = logging.FileHandler("log/core.log")
headler.setFormatter(
    logging.Formatter(
        "%(levelname)s:\t%(asctime)s [%(filename)s:%(lineno)d] - %(message)s"
    )
)
handler.addFilter(SensitiveDataFilter())
logging.root.addHandler(headler)

logging.root.setLevel(logging.DEBUG)


class OBGymCore:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 16999,
        proxies: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize the OBGymCore server.

        Args:
            host: Server host address
            port: Server port number
            proxies: Optional proxy configuration dictionary for network requests
                    Example: {"http": "http://proxy.com:8080", "https": "https://proxy.com:8080"}
        """
        self.host = host
        self.port = port
        self.proxies = proxies
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        os.makedirs("db", exist_ok=True)

        self.db = AccountSQLite("db/accounts.db")
        self.login = CASLogin(proxies=self.proxies)
        self.gym = Gym(proxies=self.proxies)
        self.job_manager = JobManager(proxies=self.proxies)
        self.job_manager.job_renew_account()

    @staticmethod
    def make_response(status: int, data: dict, message: str) -> bytes:
        """
        Create a standardized JSON response.

        Args:
            status: Response status code (0 for success)
            data: Response data dictionary
            message: Response message

        Returns:
            UTF-8 encoded JSON response
        """
        return json.dumps(
            {"status": status, "success": status == 0, "data": data, "message": message}
        ).encode("utf-8")

    def start(self) -> None:
        """
        Start the server and listen for incoming connections.
        Handles client requests and routes them to appropriate action handlers.
        """
        logging.info(
            "Scheduler started, listening for new tasks on %s:%s...",
            self.host,
            self.port,
        )

        try:
            while True:
                client_socket, addr = self.server_socket.accept()
                logging.info("New connection from %s", addr)

                data = client_socket.recv(65536)
                if not data:
                    logging.warning("No data received, skipping")
                    continue
                try:
                    task_data = json.loads(data.decode("utf-8"))
                except json.JSONDecodeError as e:
                    logging.error("Failed to decode the action data: %s", e)
                    client_socket.sendall(
                        self.make_response(
                            3, {}, f"Failed to decode the action data: {e}"
                        )
                    )
                    continue
                logging.info("Received: %s", task_data)

                action = task_data.get("action")
                kwargs = task_data.get("kwargs", {})

                func = getattr(self, f"action_{action}", None)
                if func is None or not callable(func):
                    logging.error("Action %s does not exist", action)
                    client_socket.sendall(
                        self.make_response(1, {}, f"Action {action} does not exist")
                    )
                    continue

                try:
                    ret = func(kwargs)
                except Exception as e:
                    logging.error("Error executing action %s: %s", action, e)
                    client_socket.sendall(
                        self.make_response(
                            2, {}, f"Error executing action {action}: {e}"
                        )
                    )
                else:
                    logging.info("Response: %s", ret)
                    client_socket.sendall(ret)

                client_socket.close()

        except (KeyboardInterrupt, SystemExit):
            self.stop()

    def stop(self) -> None:
        """
        Stop the server and close the socket connection.
        """
        self.server_socket.close()
        logging.info("Socket listener stopped")

    def action_add_account(self, dict_data: dict) -> bytes:
        """
        Add a new account to the database.

        Args:
            dict_data: Dictionary containing 'account' and 'password' keys

        Returns:
            Response bytes containing operation result

        Raises:
            RuntimeError: If required parameters are missing
        """
        logging.info("Action add_account called")
        try:
            account = dict_data["account"]
            password = dict_data["password"]
        except Exception as e:
            raise RuntimeError(f"Parameter error: {e}")

        ret = self.db.add_account(account, password)
        return self.make_response(0 if ret else 1, {"account": account}, "")

    def action_remove_account(self, dict_data: dict) -> bytes:
        """
        Remove an account from the database.

        Args:
            dict_data: Dictionary containing 'account' key

        Returns:
            Response bytes containing operation result

        Raises:
            RuntimeError: If required parameters are missing
        """
        logging.info("Action remove_account called")
        try:
            account = dict_data["account"]
        except Exception as e:
            raise RuntimeError(f"Parameter error: {e}")

        ret = self.db.delete_account(account)
        return self.make_response(0 if ret else 1, {"account": account}, "")

    def action_get_accounts(self, dict_data: dict) -> bytes:
        """
        Get all accounts from the database.

        Args:
            dict_data: Empty dictionary (no parameters needed)

        Returns:
            Response bytes containing list of accounts and their validity status
        """
        logging.info("Action get_accounts called")
        ret = self.db.get_all_accounts()
        data = []
        for i in ret:
            data.append({"account": i[1], "valid": i[4]})
        return self.make_response(0, data, "")

    def action_get_campus(self, dict_data: dict) -> bytes:
        """
        Get list of available campuses for a given account.

        Args:
            dict_data: Dictionary containing 'account' key

        Returns:
            Response bytes containing list of campus information

        Raises:
            RuntimeError: If required parameters are missing
            ValueError: If account is not found
        """
        logging.info("Action get_campus called")
        try:
            account = dict_data["account"]
        except Exception as e:
            raise RuntimeError(f"Parameter error: {e}")

        account_data = self.db.query_accounts(account)
        if not account_data:
            return self.make_response(3, {}, "Account not found")
        cookies_str = account_data[0][3]
        cookies = json.loads(cookies_str)

        ret = asyncio.run(self.gym.get_campus(cookies))
        data = [i.to_dict() for i in ret]
        return self.make_response(0, {"GymCampus": data}, "")

    def action_get_facility(self, dict_data: dict) -> bytes:
        """
        Get list of facilities for a given campus.

        Args:
            dict_data: Dictionary containing 'campus' and 'account' keys

        Returns:
            Response bytes containing list of facility information

        Raises:
            RuntimeError: If required parameters are missing
            ValueError: If account is not found
        """
        logging.info("Action get_facility called")
        try:
            campus_args = dict_data["campus"]
            account = dict_data["account"]
            campus = GymCampus.from_dict(campus_args)
        except Exception as e:
            raise RuntimeError(f"Parameter error: {e}")

        account_data = self.db.query_accounts(account)
        if not account_data:
            raise ValueError("Account not found")
        cookies_str = account_data[0][3]
        cookies = json.loads(cookies_str)

        ret = asyncio.run(self.gym.get_facility(campus, cookies))
        data = [i.to_dict() for i in ret]
        return self.make_response(0, {"GymFacility": data}, "")

    def action_get_area(self, dict_data: dict) -> bytes:
        """
        Get list of areas for a given facility on a specific date.

        Args:
            dict_data: Dictionary containing 'facility', 'date' and 'account' keys

        Returns:
            Response bytes containing list of area information

        Raises:
            RuntimeError: If required parameters are missing
            ValueError: If account is not found
        """
        logging.info("Action get_area called")
        try:
            facility_args = dict_data["facility"]
            date = dict_data["date"]
            account = dict_data["account"]
            facility = GymFacility.from_dict(facility_args)
        except Exception as e:
            raise RuntimeError(f"Parameter error: {e}")

        account_data = self.db.query_accounts(account)
        if not account_data:
            raise ValueError("Account not found")
        cookies_str = account_data[0][3]
        cookies = json.loads(cookies_str)

        ret = asyncio.run(self.gym.get_area(facility, date, cookies))
        data = [i.to_dict() for i in ret]
        return self.make_response(0, {"GymArea": data}, "")

    def action_renew_account(self, dict_data: dict) -> bytes:
        """
        Renew account cookies by performing a new login.

        Args:
            dict_data: Dictionary containing 'account' key

        Returns:
            Response bytes containing operation result

        Raises:
            RuntimeError: If login fails or no cookies obtained
            ValueError: If account is not found
        """
        logging.info("Action renew_account called")
        try:
            account = dict_data["account"]
        except Exception as e:
            raise RuntimeError(f"Parameter error: {e}")

        account_data = self.db.query_accounts(account)
        if not account_data:
            raise ValueError("Account not found")
        password = account_data[0][2]
        response = asyncio.run(
            self.login.get(
                account,
                password,
                "https://gym.sysu.edu.cn/app/login/pre.html",
            )
        )
        cookies_dict = {}
        for cookie in response.cookies.jar:
            if cookie.domain == "gym.sysu.edu.cn":
                cookies_dict[cookie.name] = cookie.value
        if len(cookies_dict) == 0:
            raise RuntimeError("Login failed, no cookies found")
        cookies_str = json.dumps(cookies_dict)
        self.db.set_cookies(account, cookies_str)
        self.db.set_valid(account, True)
        return self.make_response(0, {"account": account}, "")

    def action_only_book(self, dict_data: dict) -> bytes:
        """
        Create a booking job for a specific area.

        Args:
            dict_data: Dictionary containing 'area' and 'account' keys

        Returns:
            Response bytes containing job_id

        Raises:
            RuntimeError: If required parameters are missing
            ValueError: If account is not found
        """
        logging.info("Action only_book called")
        try:
            area_args = dict_data["area"]
            account = dict_data["account"]
            area = GymArea.from_dict(area_args)
        except Exception as e:
            raise RuntimeError(f"Parameter error: {e}")

        account_data = self.db.query_accounts(account)
        if not account_data:
            raise ValueError("Account not found")

        job_id = self.job_manager.job_only_book(area, account)
        return self.make_response(0, {"job_id": job_id}, "")

    def action_get_all_jobs(self, dict_data: dict) -> bytes:
        """
        Get information about all current jobs.

        Args:
            dict_data: Empty dictionary (no parameters needed)

        Returns:
            Response bytes containing list of all jobs and their status
        """
        logging.info("Action get_all_jobs called")
        jobs = self.job_manager.jobs
        data = {"all_jobs": []}
        for job in jobs.values():
            data["all_jobs"].append(
                {
                    "job_id": job.job_id,
                    "description": job.description,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                    "job_status": job.status,
                    "job_level": job.job_level,
                    "job_type": job.job_type,
                }
            )
        return self.make_response(0, data, "")

    def action_get_job_info(self, dict_data: dict) -> bytes:
        """
        Get detailed information about a specific job.

        Args:
            dict_data: Dictionary containing 'job_id' key

        Returns:
            Response bytes containing detailed job information
        """
        logging.info("Action get_job_info called")
        job_id = dict_data["job_id"]
        job = self.job_manager.jobs[job_id]
        return self.make_response(0, {"job": job.to_dict()}, "")

    def action_remove_job(self, dict_data: dict) -> bytes:
        """
        Remove a specific job.

        Args:
            dict_data: Dictionary containing 'job_id' key

        Returns:
            Response bytes containing operation result

        Raises:
            RuntimeError: If required parameters are missing
        """
        logging.info("Action remove_job called")
        try:
            job_id = dict_data["job_id"]
        except Exception as e:
            raise RuntimeError(f"Parameter error: {e}")

        self.job_manager.remove_user_job(job_id)
        return self.make_response(0, {"job_id": job_id}, "")


if __name__ == "__main__":
    OBGYM_CORE_HOST = os.getenv("OBGYM_CORE_HOST", "0.0.0.0")
    OBGYM_CORE_PORT = int(os.getenv("OBGYM_CORE_PORT", "16999"))
    OBGYM_CORE_PROXY_HOST = os.getenv("OBGYM_CORE_PROXY_HOST", None)
    OBGYM_CORE_PROXY_PORT = os.getenv("OBGYM_CORE_PROXY_PORT", None)
    if OBGYM_CORE_PROXY_HOST and OBGYM_CORE_PROXY_PORT:
        proxies = {
            "http": f"http://{OBGYM_CORE_PROXY_HOST}:{OBGYM_CORE_PROXY_PORT}",
            "https": f"http://{OBGYM_CORE_PROXY_HOST}:{OBGYM_CORE_PROXY_PORT}",
        }
    else:
        proxies = None
    core = OBGymCore(host=OBGYM_CORE_HOST, port=OBGYM_CORE_PORT, proxies=proxies)
    core.start()
