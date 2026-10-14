"""Shared data types used by every extraction module."""

from dataclasses import dataclass, field
from typing import Any

# The 8 output fields, in the order the brief lists them.
FIELDS = (
    "vendor",
    "invoice_number",
    "invoice_date",
    "due_date",
    "currency",
    "subtotal",
    "tax",
    "total",
)


@dataclass
class Found:
    """The result of looking for one field.

    value      -- what was found, or None if nothing was found
    confidence -- how sure we are, from 0.0 to 1.0
    source     -- how it was found, e.g. "label: Invoice Date"
    warnings   -- notes for a human to check
    """

    value: Any = None
    confidence: float = 0.0
    source: str = "not found"
    warnings: list[str] = field(default_factory=list)

    @property
    def found(self) -> bool:
        """True when a value was found."""
        return self.value is not None