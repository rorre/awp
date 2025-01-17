from os import PathLike
from typing import Dict, List, TypeVar, Union

from awp.parser import SubjectClass

SubjectArray = List[SubjectClass]
SubjectClasses = Dict[str, SubjectArray]
SubjectTypeClasses = Dict[str, SubjectClasses]

T = TypeVar("T")
MaybeList = Union[T, List[T]]
StrOrBytesPath = Union[str, bytes, PathLike[str], PathLike[bytes]]
