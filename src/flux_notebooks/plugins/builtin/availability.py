from __future__ import annotations

import pandas as pd
from bids import BIDSLayout

from ..base import QCPlugin


class AvailabilityPlugin:
    name = "availability"

    def run(self, layout: BIDSLayout) -> dict:
        subjects = layout.get_subjects()
        dtypes = sorted({f.datatype for f in layout.get() if f.datatype})
        rows = [
            {"sub": s, "datatype": dt, "count": len(layout.get(subject=s, datatype=dt))}
            for s in subjects
            for dt in dtypes
        ]
        df = (
            pd.DataFrame(rows)
            .pivot(index="sub", columns="datatype", values="count")
            .fillna(0)
            if rows
            else pd.DataFrame()
        )
        return {"availability": df}


plugin: QCPlugin = AvailabilityPlugin()
