from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, Iterable, Optional, Tuple

FORMULA_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*)")
CHARGE_BRACED_RE = re.compile(r"\^\{([+-]+)\}$")
TRAILING_CHARGE_RE = re.compile(r"([+-]+)$")
PARENS_RE = re.compile(r"\(([^()]*)\)")
BRACKET_RE = re.compile(r"\[([^\[\]]*)\]")



def parse_formula(formula: str) -> Dict[str, int]:
    if not formula:
        raise ValueError("formula must be non-empty")

    composition: Dict[str, int] = {}
    consumed = 0
    for match in FORMULA_TOKEN.finditer(formula):
        el, count_s = match.groups()
        count = int(count_s) if count_s else 1
        composition[el] = composition.get(el, 0) + count
        consumed += len(match.group(0))

    if consumed != len(formula):
        raise ValueError(f"Unsupported formula syntax: {formula!r}")
    return composition



def composition_to_formula(composition: Dict[str, int]) -> str:
    def key(item: Tuple[str, int]) -> Tuple[int, str]:
        el, _ = item
        if el == "C":
            return (0, el)
        if el == "H":
            return (1, el)
        return (2, el)

    parts = []
    for el, count in sorted(composition.items(), key=key):
        if count <= 0:
            continue
        parts.append(el if count == 1 else f"{el}{count}")
    return "".join(parts)



def subtract_compositions(lhs: Dict[str, int], rhs: Dict[str, int]) -> Optional[Dict[str, int]]:
    out = dict(lhs)
    for el, count in rhs.items():
        remain = out.get(el, 0) - count
        if remain < 0:
            return None
        if remain == 0:
            out.pop(el, None)
        else:
            out[el] = remain
    return out


@dataclass(frozen=True)
class ParsedToken:
    raw: str
    normalized_label: str
    formula: Optional[str]
    charge: int
    state_class: str
    excitation_label: Optional[str] = None
    excitation_energy_ev: Optional[float] = None
    tracked: bool = True



def _charge_from_marks(marks: str) -> int:
    total = 0
    for ch in marks:
        total += 1 if ch == "+" else -1
    return total



def _extract_formula_candidate(base: str) -> str:
    candidates = [base]
    if "-" in base:
        candidates.extend(part for part in base.split("-") if part)
    for candidate in candidates:
        try:
            parse_formula(candidate)
            return candidate
        except ValueError:
            continue
    return base



def parse_species_token(token: str) -> ParsedToken:
    raw = token.strip()
    if not raw:
        raise ValueError("token must be non-empty")
    text = raw.replace(" ", "")
    lower = text.lower()
    if lower in {"e", "e-", "electron"}:
        return ParsedToken(raw=raw, normalized_label="e-", formula=None, charge=-1, state_class="electron", tracked=False)
    if lower in {"hv", "hν", "photon"}:
        return ParsedToken(raw=raw, normalized_label="hν", formula=None, charge=0, state_class="photon", tracked=False)

    excitation_energy_ev = None
    excitation_label = None
    state_class = "ground"

    annotation_chunks = PARENS_RE.findall(text) + BRACKET_RE.findall(text)
    if annotation_chunks:
        for chunk in annotation_chunks:
            if "ev" in chunk.lower():
                m = re.search(r"([-+]?\d+(?:\.\d+)?)\s*eV", chunk, flags=re.I)
                if m:
                    excitation_energy_ev = float(m.group(1))
            elif chunk:
                excitation_label = chunk
                state_class = "excited"

    starred = "*" in text
    if starred and state_class == "ground":
        state_class = "excited_bucket"

    base = BRACKET_RE.sub("", PARENS_RE.sub("", text)).replace("*", "")

    charge = 0
    m = CHARGE_BRACED_RE.search(base)
    if m:
        charge = _charge_from_marks(m.group(1))
        base = CHARGE_BRACED_RE.sub("", base)
    else:
        m2 = TRAILING_CHARGE_RE.search(base)
        if m2:
            charge = _charge_from_marks(m2.group(1))
            base = TRAILING_CHARGE_RE.sub("", base)

    formula = _extract_formula_candidate(base)
    if charge > 0:
        state_class = "cation"
    elif charge < 0:
        state_class = "anion"
    elif formula and state_class == "ground" and formula in {"H", "C", "F", "Ar", "O", "N", "Cl", "Br"}:
        state_class = "atom"

    normalized = base or raw
    if charge > 0:
        normalized += "+" * charge
    elif charge < 0:
        normalized += "-" * abs(charge)
    if excitation_label:
        normalized += f"[{excitation_label}]"
    elif starred and excitation_energy_ev is not None:
        normalized += f"*[{excitation_energy_ev:g}eV]"
    elif starred:
        normalized += "*"

    return ParsedToken(
        raw=raw,
        normalized_label=normalized,
        formula=formula,
        charge=charge,
        state_class=state_class,
        excitation_label=excitation_label,
        excitation_energy_ev=excitation_energy_ev,
        tracked=True,
    )



def tracked_signature(tokens: Iterable[str]) -> tuple[str, ...]:
    out = []
    for token in tokens:
        parsed = parse_species_token(token)
        if not parsed.tracked:
            continue
        formula = parsed.formula or parsed.normalized_label
        out.append(f"{formula}|{parsed.charge}")
    return tuple(sorted(out))
