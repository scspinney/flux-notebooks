from __future__ import annotations

import pandas as pd
from bids import BIDSLayout

from ..base import QCPlugin


class FuncTasksPlugin:
    name = "func_tasks"

    def run(self, layout: BIDSLayout) -> dict:
        ents = layout.get(datatype="func", return_type="entity")
        df = pd.DataFrame(ents)
        out = (
            df.groupby(["subject", "task"]).size().unstack(fill_value=0)
            if not df.empty and "task" in df.columns
            else pd.DataFrame()
        )
        return {"func_counts": out}


plugin: QCPlugin = FuncTasksPlugin()
