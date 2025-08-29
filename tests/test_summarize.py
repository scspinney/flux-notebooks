from pathlib import Path

import pytest

from flux_notebooks.bids.summarize_bids import summarize_with_pybids


@pytest.mark.skip(reason="needs a real BIDS folder to run")
def test_summarize_with_pybids(tmp_path: Path):
    # This is a placeholder; point to a real mini BIDS dataset for CI.
    ds = tmp_path / "bids"
    ds.mkdir()
    summary = summarize_with_pybids(ds, validate=False)
    assert "subjects" in summary
