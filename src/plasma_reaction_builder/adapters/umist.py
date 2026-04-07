from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .evidence_common import ReactionEvidenceEntry, ReactionEvidenceIndex


_UMIST_SPECIAL_TOKENS = {"PHOTON", "CRP", "CRPHOT", "CR", "M"}


def _support_from_method(method: str) -> float:
    code = (method or "").strip().upper()
    if code == "M":
        return 0.62
    if code == "C":
        return 0.56
    if code == "L":
        return 0.50
    if code == "E":
        return 0.38
    return 0.42


class UmistRate22Index(ReactionEvidenceIndex):
    @classmethod
    def from_ratefile(cls, path: str, *, include_special_processes: bool = False) -> "UmistRate22Index":
        entries: List[ReactionEvidenceEntry] = []
        for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            fields = [field.strip() for field in line.split(":")]
            if len(fields) < 15:
                continue
            reaction_id = fields[0]
            reaction_type = fields[1]
            reactants = [token for token in fields[2:4] if token]
            products = [token for token in fields[4:8] if token]
            if not reactants or not products:
                continue
            if not include_special_processes and any(token.upper() in _UMIST_SPECIAL_TOKENS for token in reactants):
                continue
            method = fields[14] if len(fields) > 14 else ""
            ref_code = fields[15] if len(fields) > 15 else ""
            accuracy = fields[16] if len(fields) > 16 else ""
            note = fields[17] if len(fields) > 17 else ""
            support_score = _support_from_method(method)
            summary = f"UMIST RATE22 #{reaction_id} type={reaction_type} method={method or '?'}"
            if accuracy:
                summary += f" accuracy={accuracy}"
            if note:
                summary += f"; {note}"
            entries.append(
                ReactionEvidenceEntry(
                    source_system="umist",
                    source_name="UMIST Database for Astrochemistry",
                    reactants=reactants,
                    products=products,
                    citation=f"UMIST Rate22 reaction #{reaction_id}",
                    source_url=f"https://umistdatabase.uk/react/{reaction_id}",
                    support_score=support_score,
                    note=summary,
                    metadata={
                        "reaction_id": reaction_id,
                        "reaction_type": reaction_type,
                        "method": method,
                        "reference_code": ref_code,
                        "accuracy": accuracy,
                    },
                    acquisition_method="official_download",
                    evidence_kind="astrochemistry_network_record",
                )
            )
        return cls(entries, source_id="umist")
