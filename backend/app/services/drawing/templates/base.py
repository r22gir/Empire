"""templates/base.py — FamilyTemplate abstract base.

Phase B (Sprint 1d Phase B1) introduces the parametric family registry.
Every geometry family (drapery, roman, valance, cornice, bench-curved,
headboard-channel, etc.) implements FamilyTemplate.

Contract (matches Empire Drawing Standard v1.0):

  - validate_spec(spec) -> MissingFieldsResult
      Returns a structured list of missing required dims. NEVER defaults.
      The drawing router surfaces this as a question to the founder.
  - geometry(spec) -> GeometryResult
      Returns plan + elevation point lists. NEVER invents dims that
      weren't in the spec OR explicitly ASSUMED + listed in assumptions().
  - assumptions(spec) -> list[str]
      Human-readable list of every assumption that took effect during
      geometry generation. Rule 1 compliance.
  - layout_math(spec) -> list[MathLine]
      "subdivided overall = sum(segments)" lines for every subdivided
      dimension. Rule 3 compliance. Each MathLine carries the segments
      and gap contributions separately so closing tolerances can be
      inspected.
  - title_block(spec) -> dict
      Key/values for the title-block rows (item-specific rows).
  - render_drawing(spec) -> bytes
      Phase D hook — emits a vector PDF reportlab. NOT IMPLEMENTED IN
      B1 (per Founder direction: deferred until enforcer proof is
      available). Returns b'' in B1; Phase B2/D wires the printer.

This module is PURE (no I/O, no DB). The registry in registry.py maps
product_type -> template class. See __init__.py for the public lookup.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ── Result dataclasses (typed contracts for B2 tests) ─────────────────


@dataclass(frozen=True)
class MissingFieldsResult:
    """Returned by validate_spec. If missing_required is non-empty, the
    family must NOT render — the router returns a question instead."""
    missing_required: List[str] = field(default_factory=list)
    missing_optional: List[str] = field(default_factory=list)
    extra_dims: List[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return not self.missing_required


@dataclass(frozen=True)
class GeometryPoint:
    """A 2D point in the family drawing. Units = inches. The local origin
    is family-specific (e.g. drapery uses bottom-left of the panel;
    bench uses back-left of seat at floor). Coordinates are positive
    going right / up."""
    name: str
    x: float
    y: float
    view: str  # "plan" or "elevation" or "section"


@dataclass(frozen=True)
class GeometryEdge:
    """An edge connecting two named points. weight="outline" (default)
    or "channel" or "dim"."""
    frm: str
    to: str
    view: str
    weight: str = "outline"
    label: Optional[str] = None  # for dimension lines


@dataclass(frozen=True)
class GeometryResult:
    """The output of geometry(). points + edges are rendered as the
    family drawing. bbox is the bounding box in inches (for layout
    maths)."""
    points: List[GeometryPoint]
    edges: List[GeometryEdge]
    bbox: Tuple[float, float, float, float]  # (min_x, min_y, max_x, max_y)
    views: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class MathLine:
    """One closure line for a subdivided dimension.

      "8 × 10-49/64\" + 7 × 1/8\" = 87\" — FLUSH BOTH ENDS"

    segments is the list of (count, inches_per_segment) pairs; gaps is
    the list of (count, inches_per_gap) pairs; total is inches.
    closing_tolerance_in = total - target (must be < 1/64 for shop_ready).
    """
    label: str
    target_in: float
    segments: List[Tuple[int, float]]
    gaps: List[Tuple[int, float]]
    total: float
    note: Optional[str] = None  # "FLUSH BOTH ENDS", "FLUSH ONE END", etc.

    @property
    def closing_tolerance_in(self) -> float:
        return abs(self.total - self.target_in)


@dataclass(frozen=True)
class GeometryFamilyResult:
    """The full output of FamilyTemplate.compute(). Returned by every
    concrete family. router/printer consume this."""
    family: str
    product_type: str
    geometry: GeometryResult
    assumptions: List[str]
    layout_math: List[MathLine]
    title_block: Dict[str, str]


# ── The abstract base ─────────────────────────────────────────────────


class FamilyTemplate(ABC):
    """Base for every parametric geometry family."""

    #: Human-readable family name (e.g. "Drapery", "Roman Shades").
    family: str

    #: List of product_type strings the family handles (e.g. ["pinch_pleat", ...]).
    product_types: List[str]

    @abstractmethod
    def validate_spec(self, spec: Dict) -> MissingFieldsResult:
        """Pure: list missing dims. Does NOT raise. Family must never
        raise on partial input — router needs the structured answer."""

    @abstractmethod
    def geometry(self, spec: Dict) -> GeometryResult:
        """Pure: compute points + edges from a complete spec."""

    @abstractmethod
    def assumptions(self, spec: Dict) -> List[str]:
        """Pure: every ASSUMED label to print in the NOTES/ASSUMPTIONS
        block. Rule 1: no implicit defaults — every inferred value
        must surface here."""

    @abstractmethod
    def layout_math(self, spec: Dict) -> List[MathLine]:
        """Pure: at least one MathLine for every subdivided dim.
        Rule 3: segments + gaps must close."""

    def title_block(self, spec: Dict) -> Dict[str, str]:
        """Optional. Default: {'ITEM': product_type, 'DIMENSIONS': ...}.
        Subclasses override for family-specific rows (LEGS, CHANNELS,
        PLEATS, etc.)."""
        dims = spec.get("dims", {})
        dim_str = " x ".join(
            f'{v:.2f}"' for v in dims.values()
        ) if dims else "(unspecified)"
        return {
            "ITEM": spec.get("product_type", "—"),
            "DIMENSIONS": dim_str,
        }

    def compute(self, spec: Dict) -> GeometryFamilyResult:
        """The all-in-one: validate, then build. Raises ValueError if
        required dims are missing — caller (router) checks validate_spec
        FIRST and surfaces a question instead. compute() is for callers
        that have already validated or accept the type: ignore."""
        missing = self.validate_spec(spec)
        if not missing.is_complete:
            raise ValueError(
                f"{self.__class__.__name__}: spec is missing required dims "
                f"{missing.missing_required} — render a question first"
            )
        return GeometryFamilyResult(
            family=self.family,
            product_type=spec.get("product_type", "—"),
            geometry=self.geometry(spec),
            assumptions=self.assumptions(spec),
            layout_math=self.layout_math(spec),
            title_block=self.title_block(spec),
        )
