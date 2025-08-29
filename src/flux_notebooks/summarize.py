from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd


@dataclass(frozen=True)
class DatasetSummary:
    n_files: int
    subjects: List[str]
    sessions: List[str]
    tasks: List[str]
    datatypes: List[str]
    avail: pd.DataFrame  # sub × datatype
    func_counts: pd.DataFrame  # sub × task
