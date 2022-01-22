import asyncio
from typing import Dict, List, Union
import httpx
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:3000"
# BASE_URL = 'https://academic.ui.ac.id'


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
    DELAY = 0.5
    TIMEOUT = 5000

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=self.TIMEOUT, follow_redirects=False)

    async def _request(self, method: str, url: str, data: Union[str, dict] = None):
        futures: List[asyncio.Task] = []
        is_requesting = True
        response: httpx.Response

        def _on_request_done(resp: asyncio.Task[httpx.Response]):
            nonlocal is_requesting
            nonlocal response
            if resp.cancelled():
                return

            if is_valid_response(resp.result()):
                is_requesting = False
                response = resp

        while is_requesting:
            task = asyncio.create_task(self._client.request(method, url, data=data))
            task.add_done_callback(_on_request_done)
            futures.append(task)
            await asyncio.sleep(self.DELAY)

        await asyncio.gather(*futures, return_exceptions=False)
        return response

    async def login(self, username: str, password: str):
        await self._request(
            "POST",
            f"{BASE_URL}/main/Authentication/Index",
            {"username": username, "password": password},
        )
        if not self._client.cookies.get("siakng_cc"):
            return False

        await self._request("GET", f"{BASE_URL}/main/Authentication/ChangeRole")
        return True

    async def get_irs(self):
        return await self._request("GET", f"${BASE_URL}/main/CoursePlan/CoursePlanEdit")

    async def post_irs(self, selections: Dict[str, str]):
        if "tokens" not in selections:
            await self.get_irs()
            ...

        await self._request(
            "POST", f"${BASE_URL}/main/CoursePlan/CoursePlanSave", selections
        )
