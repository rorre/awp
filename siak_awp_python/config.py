from os import PathLike
from typing import List, Literal, TypedDict

import yaml

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Dumper, Loader  # type: ignore


class SubjectSelection(TypedDict):
    code: str
    curriculum: str
    preference: List[int]
    name: str


class Config(TypedDict):
    username: str
    password: str
    fallback: Literal["available", "lowest", "dontcare"]
    selections: List[SubjectSelection]


def load_config(path: PathLike) -> Config:
    with open(path, "r") as f:
        return yaml.load(f.read(), Loader)


def write_config(path: PathLike, config: Config):
    with open(path, "w") as f:
        yaml.dump(config, f, Dumper)
