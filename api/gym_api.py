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
import logging
from typing import Any, Dict, List, Optional, Tuple

from curl_cffi import requests
from lxml import etree


class GymAPI:
    """
    API client for SYSU Gym booking system
    Handles all direct HTTP interactions with the gym server
    """

    def __init__(self, proxies: Optional[Dict[str, str]] = None) -> None:
        """
        Initialize GymAPI client with default configurations.

        Args:
            proxies: Optional proxy configuration dictionary for network requests
                    Example: {"http": "http://proxy.com:8080", "https": "https://proxy.com:8080"}
        """
        self._session = requests.AsyncSession()
        self._proxies = proxies
        self._impersonate = "edge101"

    async def get_campus(self, cookies: Dict[str, str]) -> List[Tuple[str, str]]:
        """
        Get list of available campuses

        Args:
            cookies: Authentication cookies for the request

        Returns:
            List of tuples containing (campus_name, campus_code)
        """
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "DNT": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "sec-ch-ua": '"Microsoft Edge";v="101", "Not=A?Brand";v="8", "Chromium";v="101"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        params = {}
        logging.debug(
            "gym_api.get_campus request info:\nheaders: %s\nparams: %s\ncookies: %s",
            headers,
            params,
            cookies,
        )
        async with requests.AsyncSession() as s:
            response = await s.get(
                "https://gym.sysu.edu.cn/app/index.html",
                headers=headers,
                params=params,
                cookies=cookies,
                impersonate=self._impersonate,
                proxies=self._proxies,
            )
        logging.debug("gym_api.get_campus get response: %s", response.text)
        tree = etree.HTML(response.text)
        areas = tree.xpath("/html/body/div/section/div[2]/a")
        ret = []
        for area in areas:
            area_code = area.xpath("@href")[0].split("=")[-1]
            name = area.xpath("div[2]/h4")[0].text
            ret.append((name, area_code))
        return ret

    async def get_facility(
        self, code: str, cookies: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Get list of facilities for a specific campus

        Args:
            code: Campus code
            cookies: Authentication cookies for the request

        Returns:
            List of facility information dictionaries
        """
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "DNT": "1",
            "Referer": f"https://gym.sysu.edu.cn/app/product/arealist.html?areacode={code}",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "sec-ch-ua": '"Microsoft Edge";v="101", "Not=A?Brand";v="8", "Chromium";v="101"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        params = {
            "page": None,
            "rows": "8",
            "areacode": code,
            "remark": "defaultProList",
        }
        page = 1
        ret = []
        while True:
            params["page"] = str(page)
            logging.debug(
                "gym_api.get_facility request info:\nheaders: %s\nparams: %s\ncookies: %s",
                headers,
                params,
                cookies,
            )
            async with requests.AsyncSession() as s:
                response = await s.get(
                    "https://gym.sysu.edu.cn/app/product/productDataByarea.html",
                    headers=headers,
                    params=params,
                    cookies=cookies,
                    impersonate=self._impersonate,
                    proxies=self._proxies,
                )
            logging.debug("gym_api.get_facility get response: %s", response.text)
            data = response.json()
            ret += data
            if len(data) == 0:
                break
            page += 1
        return ret

    async def get_area(
        self, serviceid: str, date: str, cookies: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Get available areas for a specific facility on a given date

        Args:
            serviceid: Facility service ID
            date: Target date string
            cookies: Authentication cookies for the request

        Returns:
            Dictionary containing area information
        """
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "DNT": "1",
            "Referer": f"https://gym.sysu.edu.cn/app/product/show.html?id={serviceid}",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Microsoft Edge";v="101", "Not=A?Brand";v="8", "Chromium";v="101"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        params = {
            "s_date": date,
            "serviceid": serviceid,
        }
        logging.debug(
            "gym_api.get_area request info:\nheaders: %s\nparams: %s\ncookies: %s",
            headers,
            params,
            cookies,
        )
        async with requests.AsyncSession() as s:
            response = await s.get(
                "https://gym.sysu.edu.cn/app/product/findOkArea.html",
                headers=headers,
                params=params,
                cookies=cookies,
                impersonate=self._impersonate,
                proxies=self._proxies,
            )
        logging.debug("gym_api.get_area get response: %s", response.text)
        return response.json()

    async def book(
        self, serviceid: str, areaid: str, stockid: str, cookies: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Book a specific gym area

        Args:
            serviceid: Facility service ID
            areaid: Area ID
            stockid: Stock ID
            cookies: Authentication cookies for the request

        Returns:
            Dictionary containing booking result
        """
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "DNT": "1",
            "Origin": "https://gym.sysu.edu.cn",
            "Referer": f"https://gym.sysu.edu.cn/app/product/show.html?id={serviceid}",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Microsoft Edge";v="101", "Not=A?Brand";v="8", "Chromium";v="101"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        param = {
            "stockdetail": {stockid: areaid},
            "serviceid": serviceid,
            "stockid": stockid,
            "remark": "",
        }
        data = {
            "param": str(json.dumps(param)),
            "num": "1",
            "json": "true",
        }

        logging.debug(
            "gym_api.book request info:\nheaders: %s\ndata: %s\ncookies: %s",
            headers,
            data,
            cookies,
        )
        async with requests.AsyncSession() as s:
            response = await s.post(
                "https://gym.sysu.edu.cn/app/order/tobook.html",
                headers=headers,
                data=data,
                cookies=cookies,
                impersonate=self._impersonate,
                proxies=self._proxies,
            )
        logging.debug("gym_api.book get response: %s", response.text)
        return response.json()

    async def pay(self, orderid: str, cookies: Dict[str, str]) -> Dict[str, Any]:
        """
        Process payment for a booking order

        Args:
            orderid: Order ID
            cookies: Authentication cookies for the request

        Returns:
            Dictionary containing payment result
        """

        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "DNT": "1",
            "Origin": "https://gym.sysu.edu.cn",
            "Referer": f"https://gym.sysu.edu.cn/app/pay/show.html?id={orderid}&&type=sport",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Microsoft Edge";v="101", "Not=A?Brand";v="8", "Chromium";v="101"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        data_param = {
            "payid": 2,
            "orderid": orderid,
            "ctypeindex": 0,
            "password": "",
        }
        data = {
            "param": json.dumps(data_param),
            "json": "true",
        }

        logging.debug(
            "gym_api.pay request info:\nheaders: %s\ndata: %s\ncookies: %s",
            headers,
            data,
            cookies,
        )
        async with requests.AsyncSession() as s:
            response = await s.post(
                "https://gym.sysu.edu.cn/app/pay/account/topay.html",
                headers=headers,
                data=data,
                cookies=cookies,
                impersonate=self._impersonate,
                proxies=self._proxies,
            )
        logging.debug("gym_api.pay get response: %s", response.text)
        return response.json()

    async def del_order(self, orderid: str, cookies: Dict[str, str]) -> Dict[str, Any]:
        """
        Delete a booking order

        Args:
            orderid: Order ID to delete
            cookies: Authentication cookies for the request

        Returns:
            Dictionary containing deletion result
        """
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "DNT": "1",
            "Origin": "https://gym.sysu.edu.cn",
            "Referer": "https://gym.sysu.edu.cn/app/yyuser/personal.html",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Microsoft Edge";v="101", "Not=A?Brand";v="8", "Chromium";v="101"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        data = {
            "orderid": orderid,
            "json": "true",
        }
        logging.debug(
            "gym_api.del_order request info:\nheaders: %s\ndata: %s\ncookies: %s",
            headers,
            data,
            cookies,
        )
        async with requests.AsyncSession() as s:
            response = await s.post(
                "https://gym.sysu.edu.cn/app/order/delorder.html",
                headers=headers,
                data=data,
                cookies=cookies,
                impersonate=self._impersonate,
                proxies=self._proxies,
            )
        logging.debug("gym_api.del_order get response: %s", response.text)
        return response.json()

    async def get_orders(
        self, page: int, rows: int, cookies: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Get list of booking orders

        Args:
            page: Page number
            rows: Number of rows per page
            cookies: Authentication cookies for the request

        Returns:
            Dictionary containing order information
        """
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "DNT": "1",
            "Referer": "https://gym.sysu.edu.cn/app/yyuser/personal.html",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "sec-ch-ua": '"Microsoft Edge";v="101", "Not=A?Brand";v="8", "Chromium";v="101"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        params = {
            "page": str(page),
            "rows": str(rows),
            "status": "",
            "iscomment": "",
            "stockSDate": "",
            "stockEDate": "",
        }
        logging.debug(
            "gym_api.get_orders request info:\nheaders: %s\nparams: %s\ncookies: %s",
            headers,
            params,
            cookies,
        )
        async with requests.AsyncSession() as s:
            response = await s.get(
                "https://gym.sysu.edu.cn/app/yyuser/searchorder.html",
                headers=headers,
                params=params,
                cookies=cookies,
                impersonate=self._impersonate,
                proxies=self._proxies,
            )
        logging.debug("gym_api.get_orders get response: %s", response.text)
        return response.json()
