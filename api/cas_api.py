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

import io
import logging
from typing import Dict, Optional
from urllib import parse

import ddddocr
from curl_cffi import requests
from lxml import etree


class CASLogin:
    """
    Central Authentication Service (CAS) login handler for SYSU
    Manages authentication process including captcha recognition
    """

    def __init__(self) -> None:
        """
        Initialize CAS login handler with necessary components
        Sets up session, OCR tool, and default configurations
        """
        self._session = requests.AsyncSession()
        self._ocr = ddddocr.DdddOcr(beta=True, show_ad=False)

        self._proxies = None
        self._impersonate = "edge101"

        self._cookies: Optional[Dict[str, str]] = None
        self._execution: Optional[str] = None

    async def _get_pre(self, service: Optional[str] = None) -> None:
        """
        Get pre-login page and extract necessary tokens and cookies

        Args:
            service: Optional service URL for redirect after login

        Sets:
            self._execution: Login form execution token
            self._cookies: CAS domain cookies
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
        if service:
            params["service"] = service
        logging.debug(
            "cas_api._get_pre request info:\nheaders: %s\nparams: %s", headers, params
        )
        async with requests.AsyncSession() as s:
            response = await s.get(
                "https://cas.sysu.edu.cn/cas/login",
                headers=headers,
                params=params,
                impersonate=self._impersonate,
                proxies=self._proxies,
            )
        logging.debug("cas_api._get_pre get response: %s", response.text)
        tree = etree.HTML(response.text, parser=etree.HTMLParser())
        self._execution = tree.xpath('//*[@id="fm1"]/section[2]/input[1]/@value')[0]

        cookies_dict = {}
        for cookie in response.cookies.jar:
            if cookie.domain == "cas.sysu.edu.cn":
                cookies_dict[cookie.name] = cookie.value
        self._cookies = cookies_dict

    async def _get_captcha(self, service: Optional[str] = None) -> str:
        """
        Get and recognize CAPTCHA image from CAS login page

        Args:
            service: Optional service URL for referer header

        Returns:
            str: Recognized CAPTCHA text
        """
        referer = "https://cas.sysu.edu.cn/cas/login"
        if service:
            referer += f"?service={parse.quote(service)}"

        headers = {
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "DNT": "1",
            "Referer": referer,
            "Sec-Fetch-Dest": "image",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "sec-ch-ua": '"Microsoft Edge";v="101", "Not=A?Brand";v="8", "Chromium";v="101"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        logging.debug(
            "cas_api._get_captcha request info:\nheaders: %s\ncookies: %s",
            headers,
            self._cookies,
        )
        async with requests.AsyncSession() as s:
            response = await s.get(
                "https://cas.sysu.edu.cn/cas/captcha.jsp",
                headers=headers,
                cookies=self._cookies,
                impersonate=self._impersonate,
                proxies=self._proxies,
            )
        logging.debug("cas_api._get_captcha get response: %s", response.content)
        image_stream = io.BytesIO(response.content)
        result = self._ocr.classification(image_stream.read())
        logging.debug("cas_api._get_captcha ocr result: %s", result)
        return result

    async def _login(
        self, username: str, password: str, captcha: str, service: Optional[str] = None
    ) -> requests.Response:
        """
        Perform CAS login with credentials and CAPTCHA

        Args:
            username: User's login username
            password: User's login password
            captcha: Recognized CAPTCHA text
            service: Optional service URL for redirect after login

        Returns:
            Response: Login response from CAS server
        """
        referer = "https://cas.sysu.edu.cn/cas/login"
        if service:
            referer += f"?service={parse.quote(service)}"

        headers = {
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "DNT": "1",
            "Referer": referer,
            "Sec-Fetch-Dest": "image",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "sec-ch-ua": '"Microsoft Edge";v="101", "Not=A?Brand";v="8", "Chromium";v="101"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        params = {}
        if service:
            params["service"] = parse.quote(service)
        data = {
            "username": username,
            "password": password,
            "captcha": captcha,
            "execution": self._execution,
            "_eventId": "submit",
            "geolocation": "",
        }
        logging.debug(
            "cas_api._login request info:\nheaders: %s\nparams: %s\ndata: %s\ncookies: %s",
            headers,
            params,
            data,
            self._cookies,
        )
        async with requests.AsyncSession() as s:
            response = await s.post(
                "https://cas.sysu.edu.cn/cas/login",
                headers=headers,
                params=params,
                data=data,
                cookies=self._cookies,
                impersonate="edge101",
            )
        logging.debug("cas_api._login get response: %s", response.text)
        return response

    async def get(
        self, username: str, password: str, service: Optional[str] = None
    ) -> requests.Response:
        """
        Complete CAS login process including pre-login, CAPTCHA, and login

        Args:
            username: User's login username
            password: User's login password
            service: Optional service URL for redirect after login

        Returns:
            Response: Final login response from CAS server
        """
        await self._get_pre(service=service)
        captcha = await self._get_captcha(service=service)
        ret = await self._login(username, password, captcha, service=service)
        return ret
