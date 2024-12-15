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

from dataclasses import dataclass
from typing import Dict, List, Optional

from dataclasses_json import dataclass_json

from api.gym_api import GymAPI


@dataclass_json
@dataclass
class GymCampus:
    """
    Represents a gym campus location

    Attributes:
        name: Campus name
        code: Campus unique identifier code
    """

    name: str
    code: str


@dataclass_json
@dataclass
class GymFacility:
    """
    Represents a gym facility within a campus

    Attributes:
        name: Facility name
        serviceid: Facility service identifier
    """

    name: str
    serviceid: str


@dataclass_json
@dataclass
class GymArea:
    """
    Represents a specific area within a gym facility

    Attributes:
        sname: Area name
        sdate: Booking date
        timeno: Time slot number
        serviceid: Facility service identifier
        areaid: Area identifier
        stockid: Stock identifier for booking
    """

    sname: str
    sdate: str
    timeno: str
    serviceid: str
    areaid: str
    stockid: str


@dataclass_json
@dataclass
class GymOrder:
    """
    Represents a gym booking order

    Attributes:
        orderid: Order identifier
        createdate: Order creation date
    """

    orderid: str
    createdate: str


class Gym:
    """
    Main class for handling gym-related operations
    """

    def __init__(self, proxies: Optional[Dict[str, str]] = None) -> None:
        """
        Initialize Gym instance with API client
        """
        self._api = GymAPI(proxies=proxies)

    async def get_campus(self, cookie: Dict[str, str]) -> List[GymCampus]:
        """
        Retrieve list of available campuses

        Args:
            cookie: Authentication cookies for API request

        Returns:
            List of GymCampus objects representing available campuses
        """
        data = await self._api.get_campus(cookie)
        ret = []
        for i in data:
            ret.append(GymCampus(i[0], i[1]))
        return ret

    async def get_facility(
        self, campus: GymCampus, cookie: Dict[str, str]
    ) -> List[GymFacility]:
        """
        Retrieve list of facilities for a specific campus

        Args:
            campus: GymCampus object representing the target campus
            cookie: Authentication cookies for API request

        Returns:
            List of GymFacility objects representing available facilities
        """
        data = await self._api.get_facility(campus.code, cookie)
        ret = []
        for i in data:
            ret.append(GymFacility(i["name"], i["id"]))
        return ret

    async def get_area(
        self, facility: GymFacility, date: str, cookie: Dict[str, str]
    ) -> List[GymArea]:
        """
        Retrieve list of areas for a specific facility on a given date

        Args:
            facility: GymFacility object representing the target facility
            date: Date string for booking
            cookie: Authentication cookies for API request

        Returns:
            List of GymArea objects representing available areas
        """
        data = await self._api.get_area(facility.serviceid, date, cookie)
        ret = []
        for i in data["object"]:
            ret.append(
                GymArea(
                    i["sname"],
                    i["stock"]["s_date"],
                    i["stock"]["time_no"],
                    i["stock"]["serviceid"],
                    str(i["id"]),
                    str(i["stockid"]),
                )
            )
        return ret

    async def book(self, area: GymArea, cookies: Dict[str, str]) -> GymOrder:
        """
        Book a specific gym area

        Args:
            area: GymArea object representing the area to book
            cookies: Authentication cookies for API request

        Returns:
            GymOrder object representing the successful booking

        Raises:
            RuntimeError: If booking fails
        """
        data = await self._api.book(area.serviceid, area.areaid, area.stockid, cookies)
        if data["result"] == "2":
            return GymOrder(
                data["object"]["orderid"], data["object"]["order"]["createdate"]
            )
        else:
            raise RuntimeError(f"Book failed, api return: {data}")

    async def get_orders_status(
        self, order: GymOrder, cookies: Dict[str, str]
    ) -> Optional[int]:
        """
        Get the status of a specific order

        Args:
            order: GymOrder object representing the order to check
            cookies: Authentication cookies for API request

        Returns:
            Status of the order or None if not found
        """
        data = await self._api.get_orders(1, 8, cookies)
        for od in data:
            if od["orderid"] == order.orderid:
                return od["status"]
        return None

    async def pay(self, order: GymOrder, cookies: Dict[str, str]) -> bool:
        """
        Pay for a specific order

        Args:
            order: GymOrder object representing the order to pay
            cookies: Authentication cookies for API request

        Returns:
            True if payment is successful, False otherwise
        """
        data = await self._api.pay(order.orderid, cookies)
        if data["result"] == "1":
            return True
        else:
            raise RuntimeError(f"Pay failed, api return: {data}")

    async def delete_order(self, order: GymOrder, cookies: Dict[str, str]) -> bool:
        """
        Delete a specific order

        Args:
            order: GymOrder object representing the order to delete
            cookies: Authentication cookies for API request

        Returns:
            True if deletion is successful, False otherwise
        """
        data = await self._api.del_order(order.orderid, cookies)
        if data["result"] == "1":
            return True
        else:
            raise RuntimeError(f"Delete failed, api return: {data}")
