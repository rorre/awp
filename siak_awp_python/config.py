from os import PathLike
from typing import List, Literal, TypedDict
import yaml

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper  # type: ignore


class SubjectSelection(TypedDict):
    code: str
    curriculum: str
    preference: List[int]
    name: str


class Config(TypedDict):
    username: str
    password: str
    fallback: Literal["available", "lowest"]
    selections: List[SubjectSelection]


def load_config(path: PathLike) -> Config:
    with open(path, "r") as f:
        return yaml.load(f.read(), Loader)


def write_config(path: PathLike, config: Config):
    with open(path, "w") as f:
        yaml.dump(config, f, Dumper)
