from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class TranslationError:
    stage: str
    code: str
    message: str
    line: Optional[int] = None
    col: Optional[int] = None

    def __str__(self) -> str:
        pos = f" (строка {self.line}, столбец {self.col})" if self.line is not None else ""
        return f"[{self.stage}] {self.code}: {self.message}{pos}"


class TranslationException(Exception):
    def __init__(self, error: TranslationError):
        super().__init__(error.message)
        self.error = error
