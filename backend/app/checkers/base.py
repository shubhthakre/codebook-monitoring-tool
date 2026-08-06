from dataclasses import dataclass
from typing import Any


@dataclass
class CheckOutcome:
    status: str  # up | down
    message: str
    response_ms: float | None = None
    details: dict[str, Any] | None = None
