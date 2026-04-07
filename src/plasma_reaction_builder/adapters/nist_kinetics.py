from __future__ import annotations

from pathlib import Path
from typing import Iterable, List
import json
from urllib.parse import urlencode

from .evidence_common import ReactionEvidenceEntry, ReactionEvidenceIndex


class NistKineticsIndex(ReactionEvidenceIndex):
    @classmethod
    def from_json(cls, path: str) -> "NistKineticsIndex":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        entries: List[ReactionEvidenceEntry] = []
        for entry in payload.get("records", []):
            entries.append(
                ReactionEvidenceEntry(
                    source_system="nist_kinetics",
                    source_name="NIST Chemical Kinetics Database",
                    reactants=list(entry["reactants"]),
                    products=list(entry["products"]),
                    citation=entry.get("citation"),
                    source_url=entry.get("source_url"),
                    support_score=float(entry.get("support_score", 0.78)),
                    note=entry.get("note") or "Thermal gas-phase kinetics record from NIST SRD 17.",
                    metadata={
                        key: value
                        for key, value in entry.items()
                        if key not in {"reactants", "products", "citation", "source_url", "support_score", "note"}
                    },
                    acquisition_method="offline_snapshot",
                    evidence_kind="thermal_gas_phase_record",
                )
            )
        return cls(entries, source_id="nist_kinetics")

    @staticmethod
    def build_search_url(reactants: Iterable[str], products: Iterable[str] | None = None) -> str:
        reactants = list(reactants)
        products = list(products or [])
        params = {}
        for index, token in enumerate(reactants[:2], start=1):
            params[f"react{index}"] = token
        for index, token in enumerate(products[:2], start=1):
            params[f"prod{index}"] = token
        return "https://kinetics.nist.gov/kinetics/Search.jsp?" + urlencode(params)
