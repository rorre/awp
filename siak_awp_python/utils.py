from typing import List, Optional
from siak_awp_python.config import SubjectSelection

from siak_awp_python.parser import SubjectClass
import itertools


def selection_to_config(selections: List[SubjectClass]) -> List[SubjectSelection]:
    res: List[SubjectSelection] = []
    for k, grp in itertools.groupby(selections, key=lambda x: x["subject_id"]):
        sample: Optional[SubjectClass] = None
        preferences: List[int] = []
        for cls in grp:
            preferences.append(cls["idx"])
            sample = cls

        assert sample is not None
        res.append(
            {
                "code": sample["subject_id"],
                "curriculum": sample["curriculum_id"],
                "preference": preferences,
                "name": sample["subject_name"],
            }
        )
    return res
