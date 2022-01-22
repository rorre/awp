from dataclasses import dataclass
from abc import ABC, abstractstaticmethod
from typing import Any, Dict, Iterable, List, TypedDict
import re
from bs4 import BeautifulSoup

HEADER_RE = re.compile(r"(.+) - (.+) \((\d{1}) SKS, Term (\d{1})\); Kurikulum (.+)")


class ParserException(BaseException):
    def __init__(self, message: str, soup: BeautifulSoup):
        super().__init__(message)
        self.message = message
        self.soup = soup


class BaseParser(ABC):
    @abstractstaticmethod
    def parse(soup: BeautifulSoup) -> Iterable[Any]:
        pass

    @classmethod
    def from_html(cls, html: str):
        soup = BeautifulSoup(html, "lxml")
        args = cls.parse(soup)
        return cls(*args)


@dataclass
class IRSClass(BaseParser):
    subject_id: str
    class_id: str

    name: str
    capacity: int
    registrant: int
    term: int
    teachers: str

    def parse(soup: BeautifulSoup) -> Iterable[Any]:
        args = []
        inp = soup.select_one("td > input")
        if not inp:
            raise ParserException("Cannot find input.", soup)

        args.append(inp.attrs["name"])  # Subject ID
        args.append(inp.attrs["value"])  # Class ID

        children = list(soup.find_all("td"))
        args.append(children[1].text)  # Name
        args.append(int(children[3].text))  # Capacity
        args.append(int(children[4].text))  # Registrant
        args.append(int(children[5].text))  # Term
        args.append(children[8].text)  # Teachers
        return args


@dataclass
class IRSEdit(BaseParser):
    token: str
    classes: List[IRSClass]

    def parse(soup: BeautifulSoup) -> Iterable[Any]:
        irs_box = soup.select_one(".box")
        if not irs_box:
            raise ParserException("Cannot find IRS box.", soup)

        classes = []
        for cls in irs_box.select("tr"):
            if "alt" in cls.attrs["class"] or "x" in cls.attrs["class"]:
                classes.append(IRSEdit.parse(cls))

        token = soup.select_one('input[name="tokens"]')
        if not token:
            raise ParserException("Cannot find token.", soup)

        return [token.attrs["value"], classes]


class SubjectClass(TypedDict):
    subject_id: str
    curriculum_id: str
    subject_name: str
    sks: int
    name: str
    teachers: str


@dataclass
class Schedule(BaseParser):
    classes: Dict[str, List[SubjectClass]]

    def parse(soup: BeautifulSoup) -> Iterable[Any]:
        current_subject_id = ""
        current_subject_name = ""
        current_curriculum = ""
        current_sks = -1

        subject_dict: Dict[str, List[SubjectClass]] = {}

        classes = list(soup.select_one("table.box").select("tr"))
        for class_row in classes[2:]:
            is_header = "class" not in class_row.attrs
            if is_header:
                re_match = HEADER_RE.match(class_row.text.strip())
                if not re_match:
                    raise ParserException("Cannot parse header.", soup)

                current_subject_id = re_match.group(1)
                current_subject_name = re_match.group(2)
                current_curriculum = re_match.group(5)
                current_sks = int(re_match.group(3))

                subject_dict[current_subject_id] = []
            else:
                children = list(class_row.find_all("td"))
                if len(children) == 4:
                    continue
                name = children[1].text.strip()
                teachers = children[5].text.strip()

                subject_dict[current_subject_id].append(
                    {
                        "subject_id": current_subject_id,
                        "curriculum_id": current_curriculum,
                        "subject_name": current_subject_name,
                        "sks": current_sks,
                        "name": name,
                        "teachers": teachers,
                    }
                )
        return [subject_dict]
