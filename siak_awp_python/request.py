import asyncio
import ssl
from typing import TYPE_CHECKING, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup, Tag
from rich import inspect

from siak_awp_python.parser import IRSEdit, Schedule

if TYPE_CHECKING:
    from rich.console import Console

BASE_URL = "https://academic.ui.ac.id"
# BASE_URL = "http://localhost:3000"
BASE_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "content-type": "application/x-www-form-urlencoded",
    "sec-ch-ua": '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
}


class SIAKException(BaseException):
    def __init__(self, message: str, soup: Optional[BeautifulSoup | Tag] = None):
        super().__init__(message)
        self.message = message
        self.soup = soup


def is_valid_response(response: httpx.Response):
    response_text = BeautifulSoup(response.text, "lxml").text.strip()
    if response.status_code == 200:
        return not (
            "server SIAKNG sedang mengalami" in response_text
            or "SIAKNG saat ini tidak dapat diakses" in response_text
        )
    elif response.status_code == 302:
        target = (
            response.headers.get("Location") or response.headers.get("location") or ""
        )
        return "Authentication" not in target
    else:
        return False


class SIAKClient:
    DELAY = 1
    TIMEOUT = 5000

    def __init__(self, console: "Console"):
        self._console = console
        self._ssl_context = httpx.create_ssl_context()
        self._ssl_context.set_ciphers("DEFAULT@SECLEVEL=1")
        self._ssl_context.options |= ssl.OP_NO_TLSv1_3
        self._ssl_context.load_verify_locations("certigo.pem")

        self._client = httpx.AsyncClient(
            timeout=self.TIMEOUT,
            follow_redirects=False,
            headers=BASE_HEADERS,
            verify=self._ssl_context,
        )

    async def _request(
        self,
        method: str,
        url: str,
        data: Optional[dict] = None,
    ) -> httpx.Response:
        futures: List[asyncio.Task] = []
        is_requesting = True
        response: httpx.Response

        def _on_request_done(resp: asyncio.Task[httpx.Response]):
            nonlocal is_requesting
            nonlocal response
            try:
                if ex := resp.exception():
                    raise ex
                if resp.cancelled():
                    return

            except:
                return

            if is_valid_response(resp.result()):
                is_requesting = False
                [fut.cancel() for fut in futures]
                response = resp.result()

        while is_requesting:
            self._console.log("Requesting", method, url)
            task = asyncio.create_task(self._client.request(method, url, data=data))  # type: ignore
            task.add_done_callback(_on_request_done)
            futures.append(task)
            await asyncio.sleep(self.DELAY)

        try:
            await asyncio.gather(*futures, return_exceptions=False)
        except:
            pass

        return response  # type: ignore

    async def aclose(self):
        await self._client.aclose()

    def logout(self):
        self._client.cookies.clear()

    async def login(self, username: str, password: str):
        self._console.log("Logging in")
        await self._request(
            "POST",
            f"{BASE_URL}/main/Authentication/Index",
            {"u": username, "p": password},
        )
        self._console.log("Checking for cookie")
        if not self._client.cookies.get("siakng_cc"):
            raise SIAKException("Wrong password", None)

        self._console.log("Changing role")
        await self._request("GET", f"{BASE_URL}/main/Authentication/ChangeRole")
        return True

    async def get_schedule(self):
        base_schedule = await self._request("GET", f"{BASE_URL}/main/Schedule/Index")
        base_soup = BeautifulSoup(base_schedule.text, "lxml")
        latest = base_soup.select_one("select#period > option").attrs["value"]  # type: ignore

        res = await self._request(
            "GET", f"{BASE_URL}/main/Schedule/Index?period={latest}"
        )
        return Schedule.from_html(res.text)

    async def get_irs(self):
        res = await self._request("GET", f"{BASE_URL}/main/CoursePlan/CoursePlanEdit")
        soup = BeautifulSoup(res.text, "lxml").select_one("div.info")
        if soup:
            raise SIAKException("IRS not yet opened.", soup)
        return IRSEdit.from_html(res.text)

    async def post_irs(self, post_data: Dict[str, str]):
        if "tokens" not in post_data:
            irs_page = await self.get_irs()
            post_data["tokens"] = irs_page.token

        if "comment" not in post_data:
            post_data["comment"] = ""

        if "submit" not in post_data:
            post_data["submit"] = "Simpan IRS"

        await self._request(
            "POST",
            f"{BASE_URL}/main/CoursePlan/CoursePlanSave",
            post_data,
        )
