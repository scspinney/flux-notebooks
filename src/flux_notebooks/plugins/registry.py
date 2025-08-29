from __future__ import annotations

from typing import Dict, List, Type

from .base import QCPlugin
from .builtin.availability import plugin as availability_plugin
from .builtin.func_tasks import plugin as func_tasks_plugin
# bids_validator is optional (requires CLI tool); safe to import and ignore if missing
try:
    from .builtin.bids_validator import plugin as bids_validator_plugin
except Exception:  # pragma: no cover
    bids_validator_plugin = None  # type: ignore


def builtin_plugins() -> Dict[str, QCPlugin]:
    registry = {
        "availability": availability_plugin,
        "func_tasks": func_tasks_plugin,
    }
    if bids_validator_plugin is not None:
        registry["bids_validator"] = bids_validator_plugin
    return registry


def resolve(enabled: List[str]) -> List[QCPlugin]:
    reg = builtin_plugins()
    return [reg[name] for name in enabled if name in reg]
