from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from .evidence_common import ReactionEvidenceEntry, ReactionEvidenceIndex
from .http import SimpleHttpClient


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class VamdcXsamsIndex(ReactionEvidenceIndex):
    @classmethod
    def from_path(
        cls,
        path: str,
        *,
        source_name: str = "VAMDC XSAMS",
        source_system: str = "vamdc",
        support_score: Optional[float] = None,
        source_url: Optional[str] = None,
    ) -> "VamdcXsamsIndex":
        text = Path(path).read_text(encoding="utf-8")
        entries = parse_xsams_reaction_entries(
            text,
            source_name=source_name,
            source_system=source_system,
            support_score=support_score,
            source_url=source_url,
        )
        return cls(entries, source_id=source_system)


class VamdcTapClient:
    def __init__(self, *, http: Optional[SimpleHttpClient] = None) -> None:
        self.http = http or SimpleHttpClient()

    @staticmethod
    def _sync_url(url: str) -> str:
        return url.rstrip("/") if url.rstrip("/").endswith("/sync") else url.rstrip("/") + "/sync"

    def query_xsams(self, *, url: str, query: str) -> str:
        params = {
            "REQUEST": "doQuery",
            "LANG": "VSS2",
            "FORMAT": "XSAMS",
            "QUERY": query,
        }
        return self.http.get_text(self._sync_url(url), params=params)

    def head_counts(self, *, url: str, query: str) -> Dict[str, str]:
        params = {
            "REQUEST": "doQuery",
            "LANG": "VSS2",
            "FORMAT": "XSAMS",
            "QUERY": query,
        }
        headers = self.http.head_headers(self._sync_url(url), params=params)
        return {
            key: value
            for key, value in headers.items()
            if key.upper().startswith("VAMDC-")
        }

    def collect_index(
        self,
        *,
        url: str,
        queries: Iterable[str],
        source_name: str,
        source_system: str,
        support_score: Optional[float] = None,
    ) -> VamdcXsamsIndex:
        entries: List[ReactionEvidenceEntry] = []
        for query in queries:
            xsams_text = self.query_xsams(url=url, query=query)
            entries.extend(
                parse_xsams_reaction_entries(
                    xsams_text,
                    source_name=source_name,
                    source_system=source_system,
                    support_score=support_score,
                    source_url=self._sync_url(url) + "?" + urlencode({
                        "REQUEST": "doQuery",
                        "LANG": "VSS2",
                        "FORMAT": "XSAMS",
                        "QUERY": query,
                    }),
                )
            )
        return VamdcXsamsIndex(entries, source_id=source_system)



def parse_xsams_reaction_entries(
    text: str,
    *,
    source_name: str,
    source_system: str,
    support_score: Optional[float],
    source_url: Optional[str],
) -> List[ReactionEvidenceEntry]:
    root = ET.fromstring(text)
    species_labels = _species_label_map(root)
    source_refs = _source_reference_map(root)
    entries: List[ReactionEvidenceEntry] = []
    for collision in root.iter():
        if _local_name(collision.tag) not in {"Collision", "CollisionalTransition", "CollisionProcess"}:
            continue
        reactants = _role_species(collision, role="Reactant", species_labels=species_labels)
        products = _role_species(collision, role="Product", species_labels=species_labels)
        if not reactants or not products:
            continue
        ref_text = _best_collision_reference(collision, source_refs)
        kind_name = "collision"
        if source_system.lower() in {"ideadb", "vamdc_ideadb"}:
            kind_name = "dissociative_electron_attachment"
        entries.append(
            ReactionEvidenceEntry(
                source_system=source_system,
                source_name=source_name,
                reactants=reactants,
                products=products,
                citation=ref_text,
                source_url=source_url,
                support_score=support_score if support_score is not None else (0.82 if source_system.lower() in {"ideadb", "vamdc_ideadb"} else 0.70),
                note=f"VAMDC XSAMS {kind_name} record.",
                metadata={"node": source_system},
                acquisition_method="vamdc_tap" if source_url else "offline_snapshot",
                evidence_kind="collision_process_record",
            )
        )
    return entries



def _species_label_map(root: ET.Element) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    for element in root.iter():
        local = _local_name(element.tag)
        species_id = element.attrib.get("speciesID") or element.attrib.get("SpeciesID") or element.attrib.get("id")
        if not species_id or local not in {"Molecule", "Atom", "Ion", "Particle", "MolecularIon"}:
            continue
        label = _extract_species_label(element)
        if label:
            labels[species_id] = label
    return labels



def _extract_species_label(element: ET.Element) -> Optional[str]:
    values: List[str] = []
    for child in element.iter():
        local = _local_name(child.tag)
        text = (child.text or "").strip()
        if not text:
            continue
        if local in {"StoichiometricFormula", "ChemicalFormula", "Value", "Name", "ChemicalName", "OrdinaryStructuralFormula"}:
            values.append(text)
        if local == "ElementSymbol":
            values.append(text)
    for value in values:
        if any(marker in value for marker in ("(", "[", "*")):
            return value.replace(" ", "")
    for value in values:
        if any(ch.isalpha() for ch in value):
            return value.replace(" ", "")
    return values[0] if values else None



def _role_species(collision: ET.Element, *, role: str, species_labels: Dict[str, str]) -> List[str]:
    tokens: List[str] = []
    for role_element in collision.iter():
        if _local_name(role_element.tag) != role:
            continue
        refs: List[str] = []
        for child in role_element.iter():
            local = _local_name(child.tag)
            if local in {"SpeciesRef", "SpeciesID", "Species"}:
                text = (child.text or "").strip()
                if text:
                    refs.append(text)
        if refs:
            tokens.extend(species_labels.get(ref, ref) for ref in refs)
    return tokens



def _source_reference_map(root: ET.Element) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for source in root.iter():
        if _local_name(source.tag) != "Source":
            continue
        source_id = source.attrib.get("sourceID") or source.attrib.get("SourceID") or source.attrib.get("id")
        if not source_id:
            continue
        pieces: List[str] = []
        for child in source.iter():
            local = _local_name(child.tag)
            text = (child.text or "").strip()
            if not text:
                continue
            if local in {"Title", "DOI", "SourceName", "Year", "Category"}:
                pieces.append(text)
        if pieces:
            out[source_id] = "; ".join(dict.fromkeys(pieces))
    return out



def _best_collision_reference(collision: ET.Element, source_refs: Dict[str, str]) -> Optional[str]:
    refs: List[str] = []
    for child in collision.iter():
        if _local_name(child.tag) in {"SourceRef", "SourceID"}:
            text = (child.text or "").strip()
            if text and text in source_refs:
                refs.append(source_refs[text])
    if refs:
        return refs[0]
    return None
