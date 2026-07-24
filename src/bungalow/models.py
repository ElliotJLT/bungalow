"""The report data model.

A deliberate constraint runs through this file: bungalow stores no domain
knowledge. It does not know what a doubling ground rent means, what subsidence
costs, or which lease length is risky. Every severity, cost, and rule comes from
the Clearbook MCP. These types are containers for the MCP's answers plus the
light structure needed to present them as one document. Keeping the judgement in
the MCP is what stops the product from weakening it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Literal

BuyerType = Literal["first_time_buyer", "home_mover", "additional_property"]
Tenure = Literal["freehold", "leasehold"]


class Severity(IntEnum):
    """Ordered so findings sort worst-first. Values mirror the MCP's ratings.

    IntEnum so members compare directly (`max`, sorting) while `parse` and the
    lowercase `__str__` keep the MCP's names.
    """

    HIGH = 3
    MEDIUM = 2
    LOW = 1

    @classmethod
    def parse(cls, raw: str) -> Severity:
        return cls[raw.strip().upper()]

    def __str__(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class Finding:
    """One flag from an MCP tool, carried through verbatim.

    `source` is which part of the pack it came from (lease, title, survey), so
    the reader can see where a concern originates.
    """

    source: str
    issue: str
    severity: Severity
    detail: str
    action: str


@dataclass(frozen=True)
class StampDuty:
    """The MCP's stamp duty calculation. `caveat` is the one thing bungalow may
    add: a non-authoritative sanity note when the numbers look worth checking. It
    never overrides the MCP's figure."""

    total: int
    effective_rate: float
    buyer_type: str
    note: str
    caveat: str | None = None


@dataclass(frozen=True)
class Provider:
    """A conveyancer or broker returned by the MCP register search."""

    name: str
    status: str
    detail: str = ""


@dataclass
class DueDiligenceReport:
    """The finished pack: one property, one decision surface."""

    postcode: str
    price: int
    tenure: Tenure
    buyer_type: BuyerType
    generated_at: datetime
    stamp_duty: StampDuty | None = None
    providers: list[Provider] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    brief: str = ""
    notes: list[str] = field(default_factory=list)

    def sorted_findings(self) -> list[Finding]:
        """Findings worst-first, stable within a severity."""
        return sorted(self.findings, key=lambda f: f.severity.value, reverse=True)

    def high_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.HIGH]

    @property
    def overall_severity(self) -> Severity | None:
        if not self.findings:
            return None
        return max(f.severity for f in self.findings)

    @property
    def headline(self) -> str:
        sev = self.overall_severity
        if sev is Severity.HIGH:
            return "Serious issues to resolve before you spend money"
        if sev is Severity.MEDIUM:
            return "Proceed with care, some items to sort"
        if sev is Severity.LOW:
            return "Nothing unusual on what was checked"
        return "No property issues checked yet"
