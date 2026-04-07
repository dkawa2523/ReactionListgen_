from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
import csv
import re

from ..formula import parse_formula
from ..model import SpeciesPrototype

CM1_PER_EV = 8065.54429
ROMAN_NUMERALS = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8,
    "IX": 9,
    "X": 10,
}


@dataclass(slots=True)
class AsdLevel:
    spectrum: str
    element: str
    charge: int
    configuration: str
    term: str
    j_value: str
    energy_ev: float


class NistAsdBootstrapAdapter:
    def __init__(self, export_paths: Iterable[str]) -> None:
        self.levels_by_spectrum: Dict[str, List[AsdLevel]] = {}
        for path in export_paths:
            self._load_export(Path(path))

    @staticmethod
    def spectrum_from_charge(element: str, charge: int) -> str:
        roman = next(key for key, value in ROMAN_NUMERALS.items() if value == charge + 1)
        return f"{element} {roman}"

    def _load_export(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = "," if "," in sample else "\t"

        reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
        for row in reader:
            normalized = {self._norm_key(key): (value or "").strip() for key, value in row.items() if key}
            spectrum = normalized.get("spectrum") or self._infer_spectrum_from_filename(path)
            if not spectrum:
                continue
            element, charge = self._parse_spectrum(spectrum)
            level = self._coerce_energy_ev(normalized)
            if level is None:
                continue
            record = AsdLevel(
                spectrum=spectrum,
                element=element,
                charge=charge,
                configuration=normalized.get("configuration", ""),
                term=normalized.get("term", ""),
                j_value=normalized.get("j", ""),
                energy_ev=level,
            )
            self.levels_by_spectrum.setdefault(spectrum, []).append(record)

        for spectrum in list(self.levels_by_spectrum):
            self.levels_by_spectrum[spectrum] = sorted(self.levels_by_spectrum[spectrum], key=lambda item: item.energy_ev)

    @staticmethod
    def _norm_key(text: str) -> str:
        lowered = text.strip().lower()
        lowered = lowered.replace("(", " ").replace(")", " ").replace("[", " ").replace("]", " ")
        lowered = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
        return lowered

    @staticmethod
    def _infer_spectrum_from_filename(path: Path) -> Optional[str]:
        stem = path.stem.replace("-", "_")
        match = re.search(r"([A-Z][a-z]?)_([IVX]+)$", stem)
        if not match:
            return None
        return f"{match.group(1)} {match.group(2)}"

    @staticmethod
    def _parse_spectrum(spectrum: str) -> tuple[str, int]:
        parts = spectrum.split()
        if len(parts) != 2:
            raise ValueError(f"Unsupported spectrum label: {spectrum}")
        element = parts[0]
        roman = parts[1].upper()
        charge = ROMAN_NUMERALS[roman] - 1
        return element, charge

    @staticmethod
    def _coerce_numeric(value: str) -> Optional[float]:
        if not value:
            return None
        raw = value.strip().strip('"')
        if raw.startswith("="):
            raw = raw[1:].strip().strip('"')
        try:
            return float(raw)
        except ValueError:
            return None

    def _coerce_energy_ev(self, row: Dict[str, str]) -> Optional[float]:
        for key in ("level_e_v", "level_ev", "energy_ev"):
            if key in row:
                value = self._coerce_numeric(row[key])
                if value is not None:
                    return value
        for key in ("level", "energy"):
            if key in row:
                value = self._coerce_numeric(row[key])
                if value is not None:
                    return value
        for key in ("level_cm_1", "level_cm1", "energy_cm_1", "energy_cm1"):
            if key in row:
                value = self._coerce_numeric(row[key])
                if value is not None:
                    return value / CM1_PER_EV
        return None

    @staticmethod
    def _label(level: AsdLevel) -> str:
        pieces = []
        if level.term:
            pieces.append(level.term.replace(" ", ""))
        if level.j_value:
            pieces.append(level.j_value.replace(" ", ""))
        if not pieces and level.configuration:
            pieces.append(level.configuration.replace(" ", ""))
        return "_".join(pieces) if pieces else f"{level.energy_ev:.3f}eV"

    @staticmethod
    def _key_for(level: AsdLevel) -> str:
        base = level.element + ("+" * level.charge if level.charge > 0 else "")
        if abs(level.energy_ev) < 1e-9:
            return base
        return f"{base}[{NistAsdBootstrapAdapter._label(level)}]"

    @staticmethod
    def _display_name(level: AsdLevel) -> str:
        base = level.element + ("+" * level.charge if level.charge > 0 else "")
        if abs(level.energy_ev) < 1e-9:
            return base
        return f"{base} {NistAsdBootstrapAdapter._label(level)}"

    def bootstrap(self, formulas: Iterable[str], *, max_ion_charge: int, max_levels_per_spectrum: int) -> List[SpeciesPrototype]:
        elements = sorted({element for formula in formulas for element in parse_formula(formula).keys()})
        out: List[SpeciesPrototype] = []
        for element in elements:
            for charge in range(0, max_ion_charge + 1):
                spectrum = self.spectrum_from_charge(element, charge)
                levels = self.levels_by_spectrum.get(spectrum, [])[:max_levels_per_spectrum]
                for level in levels:
                    key = self._key_for(level)
                    state_class = "atom" if charge == 0 and abs(level.energy_ev) < 1e-9 else "cation" if charge > 0 else "excited"
                    tags = ["asd_bootstrap", "atomic"]
                    if charge > 0:
                        tags.append("ion")
                    if abs(level.energy_ev) >= 1e-9:
                        tags.append("excited")
                    out.append(
                        SpeciesPrototype(
                            key=key,
                            display_name=self._display_name(level),
                            formula=element,
                            charge=charge,
                            state_class=state_class,
                            excitation_label=None if abs(level.energy_ev) < 1e-9 else self._label(level),
                            excitation_energy_ev=None if abs(level.energy_ev) < 1e-9 else level.energy_ev,
                            tags=tags,
                        )
                    )
        unique = {proto.key: proto for proto in out}
        return list(unique.values())
