import itertools
import re
import sys
from abc import ABC, abstractstaticmethod
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, TypedDict

from bs4 import BeautifulSoup

HEADER_RE = re.compile(
    r"([A-Z]{4}\d{6}) - (.+) \((\d{1}) SKS, Term (\d{1})\); Kurikulum (.+)"
)


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

    def parse(soup: BeautifulSoup) -> Iterable[Any]:
        args = []
        inp = soup.select_one("td > input")
        if not inp:
            raise ParserException("Cannot find input.", soup)

        args.append(inp.attrs["name"])  # Subject ID
        args.append(inp.attrs["value"])  # Class ID

        children = list(soup.select("td"))
        args.append(children[1].text.strip())  # Name
        if len(children) == 7:
            args.append(sys.maxsize)  # Capacity
        else:
            args.append(int(children[3].text.strip()))  # Capacity

        args.append(int(children[4].text.strip()))  # Registrant

        return args


@dataclass
class IRSEdit(BaseParser):
    token: str
    classes: List[IRSClass]

    @property
    def classes_by_id(self):
        return {
            k: list(g)
            for k, g in itertools.groupby(self.classes, lambda x: x.subject_id)
        }

    def get_classes_by_id(self, subject_id: str, curriculum: str):
        return self.classes_by_id[f"c[{subject_id}_{curriculum}]"]

    def parse(soup: BeautifulSoup) -> Iterable[Any]:
        print(soup)
        irs_box = soup.select(".box")
        if not irs_box:
            raise ParserException("Cannot find IRS box.", soup)

        classes = []
        for box in irs_box:
            for cls in box.select("tr"):
                if "class" in cls.attrs:
                    classes.append(IRSClass(*IRSClass.parse(cls)))

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
    idx: int


def _parse_box(box: BeautifulSoup):
    current_subject_id = ""
    current_subject_name = ""
    current_curriculum = ""
    current_sks = -1
    idx = 0

    result: Dict[str, List[SubjectClass]] = {}
    classes = list(box.select("tr"))
    for class_row in classes[2:]:
        is_header = "class" not in class_row.attrs
        if is_header:
            re_match = HEADER_RE.match(class_row.text.strip())
            if not re_match:
                raise ParserException("Cannot parse header.", box)

            current_subject_id = re_match.group(1)
            current_subject_name = re_match.group(2)
            current_curriculum = re_match.group(5)
            current_sks = int(re_match.group(3))

            result[current_subject_name] = []
            idx = 0
        else:
            children = list(class_row.select("td"))
            if len(children) == 4:
                continue
            name = children[1].text.strip()

            result[current_subject_name].append(
                {
                    "subject_id": current_subject_id,
                    "curriculum_id": current_curriculum,
                    "subject_name": current_subject_name,
                    "sks": current_sks,
                    "name": name,
                    "idx": idx,
                }
            )
            idx += 1
    return result


@dataclass
class Schedule(BaseParser):
    classes: Dict[str, Dict[str, List[SubjectClass]]]

    def parse(soup: BeautifulSoup) -> Iterable[Any]:
        subject_dict: Dict[str, List[SubjectClass]] = {}

        tags = soup.select_one("#ti_m1").select("h3")
        boxes = list(soup.select("table.box"))

        for i in range(len(boxes)):
            title_strings = list(tags[i].stripped_strings)
            subject_dict[title_strings[0]] = _parse_box(boxes[i])

        return [subject_dict]
