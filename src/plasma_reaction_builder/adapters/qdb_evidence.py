from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from .evidence_common import ReactionEvidenceEntry, ReactionEvidenceIndex
from .http import SimpleHttpClient


class QdbEvidenceIndex(ReactionEvidenceIndex):
    @classmethod
    def from_json(cls, path: str) -> "QdbEvidenceIndex":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        entries: List[ReactionEvidenceEntry] = []
        for entry in payload.get("records", []):
            entries.append(
                ReactionEvidenceEntry(
                    source_system="qdb",
                    source_name="Quantemol-DB",
                    reactants=list(entry["reactants"]),
                    products=list(entry["products"]),
                    citation=entry.get("citation"),
                    source_url=entry.get("source_url"),
                    support_score=float(entry.get("support_score", 0.90)),
                    note=entry.get("note") or "Validated chemistry or reaction entry from Quantemol-DB.",
                    metadata={
                        key: value
                        for key, value in entry.items()
                        if key not in {"reactants", "products", "citation", "source_url", "support_score", "note"}
                    },
                    acquisition_method="offline_snapshot",
                    evidence_kind="validated_chemistry_record",
                )
            )
        return cls(entries, source_id="qdb")


class QdbApiClient:
    BASE_URL = "https://www.quantemoldb.com/reactions/api/"

    def __init__(self, *, api_key: str, http: Optional[SimpleHttpClient] = None) -> None:
        self.api_key = api_key
        self.http = http or SimpleHttpClient()

    def fetch_chemistry_raw(self, chemistry_id: int, *, no_xsecs: bool = True, all_datasets: bool = True) -> str:
        params = {
            "key": self.api_key,
            "chemistry_id": chemistry_id,
            "no_xsecs": "true" if no_xsecs else "false",
            "all_datasets": "true" if all_datasets else "false",
        }
        return self.http.get_text(self.BASE_URL, params=params)
