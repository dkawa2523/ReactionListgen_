from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional
import csv
import io
import re
import zipfile

from .evidence_common import ReactionEvidenceEntry, ReactionEvidenceIndex


_FLOAT_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?$")
_KIDA_SPECIAL_TOKENS = {"PHOTON", "CRP", "CRPHOT", "GRAIN", "E-"}


def _is_number(token: str) -> bool:
    return bool(_FLOAT_RE.match(token.strip()))


def _support_from_status(status: str, method: str) -> float:
    text = (status or "").strip().lower()
    if "recommended" in text:
        return 0.66
    if "valid" in text:
        return 0.58
    if "not rated" in text or "unknown" in text:
        return 0.42
    method_text = (method or "").strip().lower()
    if "measurement" in method_text:
        return 0.60
    if "theoretical" in method_text or "review" in method_text:
        return 0.54
    if "estimat" in method_text:
        return 0.40
    return 0.48


class KidaNetworkIndex(ReactionEvidenceIndex):
    @classmethod
    def from_file(cls, path: str, *, include_special_processes: bool = False) -> "KidaNetworkIndex":
        target = Path(path)
        if target.suffix.lower() == ".zip":
            text = _read_kida_zip(target)
        else:
            text = target.read_text(encoding="utf-8")
        entries = list(_parse_kida_text(text, include_special_processes=include_special_processes))
        return cls(entries, source_id="kida")



def _read_kida_zip(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            lowered = name.lower()
            if "gas_reactions" in lowered:
                return archive.read(name).decode("utf-8")
    raise FileNotFoundError("Could not find gas_reactions file inside KIDA zip archive")



def _parse_kida_text(text: str, *, include_special_processes: bool) -> Iterable[ReactionEvidenceEntry]:
    lines = [line.rstrip("\n") for line in text.splitlines()]
    non_comment = [line for line in lines if line.strip() and not line.lstrip().startswith(("#", "!", "%"))]
    if not non_comment:
        return []
    sample = "\n".join(non_comment[:8])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ""
    if delimiter:
        yield from _parse_delimited_kida(non_comment, delimiter=delimiter, include_special_processes=include_special_processes)
        return
    for line in non_comment:
        entry = _parse_whitespace_kida_line(line, include_special_processes=include_special_processes)
        if entry is not None:
            yield entry



def _parse_delimited_kida(lines: List[str], *, delimiter: str, include_special_processes: bool) -> Iterable[ReactionEvidenceEntry]:
    header = [cell.strip().lower() for cell in next(csv.reader([lines[0]], delimiter=delimiter))]
    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=delimiter)
    if not header or not any("react" in cell for cell in header):
        for line in lines:
            entry = _parse_whitespace_kida_line(line, include_special_processes=include_special_processes)
            if entry is not None:
                yield entry
        return

    for row in reader:
        normalized = {str(key).strip().lower(): (value or "").strip() for key, value in row.items() if key}
        reactants = [normalized.get("reactant 1") or normalized.get("reactant1") or normalized.get("reactant_1"), normalized.get("reactant 2") or normalized.get("reactant2") or normalized.get("reactant_2")]
        reactants = [token for token in reactants if token]
        products: List[str] = []
        for index in range(1, 7):
            products.extend(
                token
                for token in [
                    normalized.get(f"product {index}"),
                    normalized.get(f"product{index}"),
                    normalized.get(f"product_{index}"),
                ]
                if token
            )
        if not reactants or not products:
            continue
        if not include_special_processes and any(token.upper() in _KIDA_SPECIAL_TOKENS for token in reactants):
            continue
        reaction_id = normalized.get("id") or normalized.get("reaction id") or normalized.get("reaction_id") or normalized.get("num")
        status = normalized.get("status") or normalized.get("quality") or ""
        method = normalized.get("method") or ""
        support_score = _support_from_status(status, method)
        note = f"KIDA network record{f' #{reaction_id}' if reaction_id else ''}"
        if status:
            note += f" status={status}"
        if method:
            note += f" method={method}"
        yield ReactionEvidenceEntry(
            source_system="kida",
            source_name="KIDA",
            reactants=reactants,
            products=products,
            citation=(f"KIDA reaction #{reaction_id}" if reaction_id else "KIDA network record"),
            support_score=support_score,
            note=note,
            metadata={"reaction_id": reaction_id, "status": status, "method": method},
            acquisition_method="official_download",
            evidence_kind="astrochemistry_network_record",
        )



def _parse_whitespace_kida_line(line: str, *, include_special_processes: bool) -> Optional[ReactionEvidenceEntry]:
    text = line.strip()
    if not text:
        return None
    fields = text.split()
    if len(fields) < 6:
        return None
    reaction_id = fields[0] if fields[0].isdigit() else None
    type_code = fields[1] if reaction_id is not None else None
    species_tokens = fields[2:] if reaction_id is not None else fields
    numeric_start = None
    for index, token in enumerate(species_tokens):
        if _is_number(token):
            numeric_start = index
            break
    if numeric_start is None or numeric_start < 3:
        return None
    prefix = species_tokens[:numeric_start]
    if len(prefix) < 3:
        return None
    reactants = prefix[:2]
    products = prefix[2:]
    if not include_special_processes and any(token.upper() in _KIDA_SPECIAL_TOKENS for token in reactants):
        return None
    numeric_tail = species_tokens[numeric_start:]
    support_score = 0.48
    note = f"KIDA network record{f' #{reaction_id}' if reaction_id else ''}"
    if type_code is not None:
        note += f" type={type_code}"
    if numeric_tail:
        note += f"; parameter_count={len(numeric_tail)}"
    return ReactionEvidenceEntry(
        source_system="kida",
        source_name="KIDA",
        reactants=reactants,
        products=products,
        citation=(f"KIDA reaction #{reaction_id}" if reaction_id else "KIDA network record"),
        support_score=support_score,
        note=note,
        metadata={"reaction_id": reaction_id, "type_code": type_code},
        acquisition_method="official_download",
        evidence_kind="astrochemistry_network_record",
    )
