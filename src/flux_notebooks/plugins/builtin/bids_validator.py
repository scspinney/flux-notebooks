from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

from bids import BIDSLayout

from ..base import QCPlugin


class BIDSValidatorPlugin:
    name = "bids_validator"

    def run(self, layout: BIDSLayout) -> dict:
        # Requires bids-validator CLI in PATH
        if shutil.which("bids-validator") is None:
            return {"validator": {"error": "bids-validator CLI not found in PATH"}}
        root = Path(layout.root)
        cmd = ["bids-validator", "--json", str(root)]
        try:
            out = subprocess.check_output(cmd, text=True)
            data: Dict[str, Any] = json.loads(out)
            # Return a compact summary
            summary = {
                "errors": len(data.get("issues", {}).get("errors", [])),
                "warnings": len(data.get("issues", {}).get("warnings", [])),
            }
            return {"validator": summary}
        except subprocess.CalledProcessError as e:  # pragma: no cover
            return {"validator": {"error": f"validator failed: {e}"}}


plugin: QCPlugin = BIDSValidatorPlugin()
