import asyncio
import ssl
from typing import TYPE_CHECKING, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup, Tag
from rich import inspect

from awp.parser import IRSEdit, Schedule

if TYPE_CHECKING:
    from rich.console import Console


CA = """-----BEGIN CERTIFICATE-----
MIIGEzCCA/ugAwIBAgIQfVtRJrR2uhHbdBYLvFMNpzANBgkqhkiG9w0BAQwFADCB
iDELMAkGA1UEBhMCVVMxEzARBgNVBAgTCk5ldyBKZXJzZXkxFDASBgNVBAcTC0pl
cnNleSBDaXR5MR4wHAYDVQQKExVUaGUgVVNFUlRSVVNUIE5ldHdvcmsxLjAsBgNV
BAMTJVVTRVJUcnVzdCBSU0EgQ2VydGlmaWNhdGlvbiBBdXRob3JpdHkwHhcNMTgx
MTAyMDAwMDAwWhcNMzAxMjMxMjM1OTU5WjCBjzELMAkGA1UEBhMCR0IxGzAZBgNV
BAgTEkdyZWF0ZXIgTWFuY2hlc3RlcjEQMA4GA1UEBxMHU2FsZm9yZDEYMBYGA1UE
ChMPU2VjdGlnbyBMaW1pdGVkMTcwNQYDVQQDEy5TZWN0aWdvIFJTQSBEb21haW4g
VmFsaWRhdGlvbiBTZWN1cmUgU2VydmVyIENBMIIBIjANBgkqhkiG9w0BAQEFAAOC
AQ8AMIIBCgKCAQEA1nMz1tc8INAA0hdFuNY+B6I/x0HuMjDJsGz99J/LEpgPLT+N
TQEMgg8Xf2Iu6bhIefsWg06t1zIlk7cHv7lQP6lMw0Aq6Tn/2YHKHxYyQdqAJrkj
eocgHuP/IJo8lURvh3UGkEC0MpMWCRAIIz7S3YcPb11RFGoKacVPAXJpz9OTTG0E
oKMbgn6xmrntxZ7FN3ifmgg0+1YuWMQJDgZkW7w33PGfKGioVrCSo1yfu4iYCBsk
Haswha6vsC6eep3BwEIc4gLw6uBK0u+QDrTBQBbwb4VCSmT3pDCg/r8uoydajotY
uK3DGReEY+1vVv2Dy2A0xHS+5p3b4eTlygxfFQIDAQABo4IBbjCCAWowHwYDVR0j
BBgwFoAUU3m/WqorSs9UgOHYm8Cd8rIDZsswHQYDVR0OBBYEFI2MXsRUrYrhd+mb
+ZsF4bgBjWHhMA4GA1UdDwEB/wQEAwIBhjASBgNVHRMBAf8ECDAGAQH/AgEAMB0G
A1UdJQQWMBQGCCsGAQUFBwMBBggrBgEFBQcDAjAbBgNVHSAEFDASMAYGBFUdIAAw
CAYGZ4EMAQIBMFAGA1UdHwRJMEcwRaBDoEGGP2h0dHA6Ly9jcmwudXNlcnRydXN0
LmNvbS9VU0VSVHJ1c3RSU0FDZXJ0aWZpY2F0aW9uQXV0aG9yaXR5LmNybDB2Bggr
BgEFBQcBAQRqMGgwPwYIKwYBBQUHMAKGM2h0dHA6Ly9jcnQudXNlcnRydXN0LmNv
bS9VU0VSVHJ1c3RSU0FBZGRUcnVzdENBLmNydDAlBggrBgEFBQcwAYYZaHR0cDov
L29jc3AudXNlcnRydXN0LmNvbTANBgkqhkiG9w0BAQwFAAOCAgEAMr9hvQ5Iw0/H
ukdN+Jx4GQHcEx2Ab/zDcLRSmjEzmldS+zGea6TvVKqJjUAXaPgREHzSyrHxVYbH
7rM2kYb2OVG/Rr8PoLq0935JxCo2F57kaDl6r5ROVm+yezu/Coa9zcV3HAO4OLGi
H19+24rcRki2aArPsrW04jTkZ6k4Zgle0rj8nSg6F0AnwnJOKf0hPHzPE/uWLMUx
RP0T7dWbqWlod3zu4f+k+TY4CFM5ooQ0nBnzvg6s1SQ36yOoeNDT5++SR2RiOSLv
xvcRviKFxmZEJCaOEDKNyJOuB56DPi/Z+fVGjmO+wea03KbNIaiGCpXZLoUmGv38
sbZXQm2V0TP2ORQGgkE49Y9Y3IBbpNV9lXj9p5v//cWoaasm56ekBYdbqbe4oyAL
l6lFhd2zi+WJN44pDfwGF/Y4QA5C5BIG+3vzxhFoYt/jmPQT2BVPi7Fp2RBgvGQq
6jG35LWjOhSbJuMLe/0CjraZwTiXWTb2qHSihrZe68Zk6s+go/lunrotEbaGmAhY
LcmsJWTyXnW0OMGuf1pGg+pRyrbxmRE1a6Vqe8YAsOf4vmSyrcjC8azjUeqkk+B5
yOGBQMkKW+ESPMFgKuOXwIlCypTPRpgSabuY0MLTDXJLR27lk8QyKGOHQ+SwMj4K
00u/I5sUKUErmgQfky3xxzlIPK1aEn8=
-----END CERTIFICATE-----"""

BASE_URL = "https://academic.ui.ac.id"
# BASE_URL = "http://localhost:3000"
BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Origin": "https://academic.ui.ac.id",
    "Referer": "https://academic.ui.ac.id/main/Authentication/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


class SIAKException(BaseException):
    def __init__(self, message: str, soup: Optional[BeautifulSoup | Tag] = None):
        super().__init__(message)
        self.message = message
        self.soup = soup


def is_valid_response(response: httpx.Response):
    try:
        response_text = BeautifulSoup(response.text, "lxml").text.strip()
    except:
        response_text = response.text.strip()

    if response.status_code == 200:
        return not (
            "server SIAKNG sedang mengalami" in response_text
            or "SIAKNG saat ini tidak dapat diakses" in response_text
            or "The requested URL was rejected." in response_text
            or "This question is for testing whether you" in response_text
        )
    elif response.status_code == 302:
        target = response.headers.get("Location") or response.headers.get("location") or ""
        return "Authentication" not in target
    else:
        return False


class SIAKClient:
    DELAY = 5
    TIMEOUT = 5000

    def __init__(self, console: "Console"):
        self._console = console
        self._ssl_context = httpx.create_ssl_context()
        self._ssl_context.set_ciphers("DEFAULT@SECLEVEL=0")
        self._ssl_context.minimum_version = ssl.TLSVersion.TLSv1
        self._ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
        self._ssl_context.options = ssl.PROTOCOL_TLS & ssl.OP_NO_TLSv1_3
        self._ssl_context.load_verify_locations(cadata=CA)

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
                if resp.cancelled():
                    return
                if ex := resp.exception():
                    raise ex

            except Exception as e:
                print(e)
                return

            if is_valid_response(resp.result()):
                is_requesting = False
                [fut.cancel() for fut in futures]
                response = resp.result()

        while is_requesting:
            self._console.log("Requesting", method, url)

            cookie = self.get_cookies()
            self._client.cookies.clear()
            if cookie.get("Mojavi") and cookie.get("siakng_cc"):
                self.set_cookies(cookie)

            task = asyncio.create_task(self._client.request(method, url, data=data, headers=BASE_HEADERS))  # type: ignore
            task.add_done_callback(_on_request_done)
            futures.append(task)
            await asyncio.sleep(self.DELAY)

        try:
            await asyncio.gather(*futures, return_exceptions=False)
        except:
            pass

        return response  # type: ignore  # noqa: F821

    async def aclose(self):
        await self._client.aclose()

    def logout(self):
        self._client.cookies.clear()

    def get_cookies(self) -> Dict[str, str]:
        return {
            "Mojavi": self._client.cookies.get("Mojavi"),  # type: ignore
            "siakng_cc": self._client.cookies.get("siakng_cc"),  # type: ignore
        }

    def set_cookies(self, cookies: Dict[str, str]):
        domain = urlparse(BASE_URL).netloc
        self._client.cookies.set("Mojavi", cookies["Mojavi"], domain=domain, path="/")
        self._client.cookies.set("siakng_cc", cookies["siakng_cc"], domain=domain, path="/")

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

        res = await self._request("GET", f"{BASE_URL}/main/Schedule/Index?period={latest}")
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
