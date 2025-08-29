from __future__ import annotations

from typing import Protocol


class QCPlugin(Protocol):
    name: str

    def run(self, *args, **kwargs) -> dict:
        ...
