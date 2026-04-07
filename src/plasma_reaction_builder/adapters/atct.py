from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional
import csv

from ..model import ReactionRecord, SpeciesState
from ..provenance import EvidenceRecord


@dataclass(slots=True)
class AtctEntry:
    species_key: Optional[str]
    display_name: Optional[str]
    formula: Optional[str]
    delta_hf_298_kj_mol: Optional[float]
    delta_hf_0_kj_mol: Optional[float]
    version: Optional[str]
    doi: Optional[str]
    source_url: Optional[str]


class AtctSnapshotAdapter:
    def __init__(self, snapshot_path: str) -> None:
        self.entries: list[AtctEntry] = []
        self.by_key: Dict[str, AtctEntry] = {}
        self.by_name: Dict[str, AtctEntry] = {}
        self.by_formula: Dict[str, AtctEntry] = {}
        self._load(Path(snapshot_path))

    def _load(self, path: Path) -> None:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                entry = AtctEntry(
                    species_key=(row.get("species_key") or "").strip() or None,
                    display_name=(row.get("display_name") or "").strip() or None,
                    formula=(row.get("formula") or "").strip() or None,
                    delta_hf_298_kj_mol=self._coerce(row.get("delta_hf_298_kj_mol")),
                    delta_hf_0_kj_mol=self._coerce(row.get("delta_hf_0_kj_mol")),
                    version=(row.get("version") or "").strip() or None,
                    doi=(row.get("doi") or "").strip() or None,
                    source_url=(row.get("source_url") or "").strip() or None,
                )
                self.entries.append(entry)
                if entry.species_key:
                    self.by_key[entry.species_key.lower()] = entry
                if entry.display_name:
                    self.by_name[entry.display_name.lower()] = entry
                if entry.formula and entry.formula not in self.by_formula:
                    self.by_formula[entry.formula] = entry

    @staticmethod
    def _coerce(value: Optional[str]) -> Optional[float]:
        if value is None or value == "":
            return None
        return float(value)

    def lookup_species(self, state: SpeciesState) -> Optional[AtctEntry]:
        if state.prototype_key.lower() in self.by_key:
            return self.by_key[state.prototype_key.lower()]
        if state.display_name.lower() in self.by_name:
            return self.by_name[state.display_name.lower()]
        if state.charge == 0 and state.excitation_label is None and state.state_class in {"ground", "atom"}:
            return self.by_formula.get(state.formula)
        return None

    def enrich_species(self, state: SpeciesState) -> bool:
        entry = self.lookup_species(state)
        if not entry:
            return False
        state.thermo.delta_hf_298_kj_mol = entry.delta_hf_298_kj_mol
        state.thermo.delta_hf_0_kj_mol = entry.delta_hf_0_kj_mol
        state.thermo.source_version = entry.version
        state.thermo.doi = entry.doi
        state.thermo.source_url = entry.source_url
        state.evidence.append(
            EvidenceRecord(
                source_system="atct",
                source_name="Active Thermochemical Tables",
                acquisition_method="offline_snapshot",
                evidence_kind="evaluated_database",
                support_score=0.94,
                source_url=entry.source_url,
                locator=entry.species_key or entry.display_name or state.prototype_key,
                citation=f"ATcT {entry.version}" if entry.version else "ATcT",
                note="Thermochemical values attached from ATcT snapshot.",
            )
        )
        return True

    def reaction_delta_h(self, reaction: ReactionRecord, states_by_id: Dict[str, SpeciesState]) -> Optional[float]:
        reactants = [states_by_id[state_id] for state_id in reaction.reactant_state_ids]
        products = [states_by_id[state_id] for state_id in reaction.product_state_ids]
        if any(state.thermo.delta_hf_298_kj_mol is None for state in reactants + products):
            return None
        product_sum = sum(state.thermo.delta_hf_298_kj_mol or 0.0 for state in products)
        reactant_sum = sum(state.thermo.delta_hf_298_kj_mol or 0.0 for state in reactants)
        return product_sum - reactant_sum
