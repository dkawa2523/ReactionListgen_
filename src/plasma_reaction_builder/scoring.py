from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from .formula import parse_formula, parse_species_token
from .model import ReactionRecord, ReactionTemplate, SpeciesState
from .provenance import ConfidenceScore, EvidenceRecord



def _sum_charge(tokens: Iterable[str]) -> int:
    total = 0
    for token in tokens:
        total += parse_species_token(token).charge
    return total



def _sum_atoms(tokens: Iterable[str]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for token in tokens:
        parsed = parse_species_token(token)
        if not parsed.formula:
            continue
        try:
            comp = parse_formula(parsed.formula)
        except ValueError:
            continue
        for el, count in comp.items():
            out[el] = out.get(el, 0) + count
    return out



def is_balanced(lhs_tokens: Iterable[str], rhs_tokens: Iterable[str]) -> bool:
    lhs = list(lhs_tokens)
    rhs = list(rhs_tokens)
    return _sum_charge(lhs) == _sum_charge(rhs) and _sum_atoms(lhs) == _sum_atoms(rhs)



def _evidence_bonus(evidence: List[EvidenceRecord]) -> float:
    if not evidence:
        return 0.05
    avg = sum(float(record.support_score) for record in evidence) / len(evidence)
    return max(0.0, min(0.25, 0.25 * avg))



def _threshold_bonus(required_projectile: Optional[str], threshold_ev: Optional[float], electron_max_ev: float, ion_max_ev: float) -> float:
    if threshold_ev is None:
        return 0.02
    available = electron_max_ev if required_projectile == "e-" else ion_max_ev
    if threshold_ev <= available:
        return 0.10
    if threshold_ev <= available * 1.15:
        return 0.03
    return -0.10



def _thermo_bonus(delta_h_kj_mol: Optional[float], required_projectile: Optional[str]) -> float:
    if delta_h_kj_mol is None:
        return 0.0
    if required_projectile == "e-":
        if delta_h_kj_mol <= 0:
            return 0.05
        if delta_h_kj_mol <= 300:
            return 0.02
        if delta_h_kj_mol <= 700:
            return -0.03
        return -0.08

    if delta_h_kj_mol <= 0:
        return 0.08
    if delta_h_kj_mol <= 100:
        return 0.04
    if delta_h_kj_mol <= 200:
        return -0.02
    return -0.10



def score_reaction(
    *,
    template: ReactionTemplate,
    reaction: ReactionRecord,
    generation: int,
    electron_max_ev: float,
    ion_max_ev: float,
) -> ConfidenceScore:
    balance_bonus = 0.12 if is_balanced(reaction.lhs_tokens, reaction.rhs_tokens) else -0.20
    evidence_bonus = _evidence_bonus(reaction.evidence)
    threshold_bonus = _threshold_bonus(template.required_projectile, reaction.threshold_ev, electron_max_ev, ion_max_ev)
    thermo_bonus = _thermo_bonus(reaction.delta_h_kj_mol, template.required_projectile)
    generation_penalty = min(0.25, 0.05 * max(generation - 1, 0))
    return ConfidenceScore.build(
        base_score=template.base_confidence,
        evidence_bonus=evidence_bonus,
        balance_bonus=balance_bonus,
        threshold_bonus=threshold_bonus,
        thermo_bonus=thermo_bonus,
        generation_penalty=generation_penalty,
    )



def score_species(state: SpeciesState, parent_reaction: Optional[ReactionRecord] = None) -> ConfidenceScore:
    base = max(0.30, (parent_reaction.confidence.final_score - 0.05) if parent_reaction and parent_reaction.confidence else 0.55)
    evidence_bonus = _evidence_bonus(state.evidence)
    balance_bonus = 0.08
    threshold_bonus = 0.0
    thermo_bonus = 0.05 if state.thermo.delta_hf_298_kj_mol is not None else 0.0
    generation_penalty = min(0.30, 0.04 * max(state.generation - 1, 0))
    return ConfidenceScore.build(
        base_score=base,
        evidence_bonus=evidence_bonus,
        balance_bonus=balance_bonus,
        threshold_bonus=threshold_bonus,
        thermo_bonus=thermo_bonus,
        generation_penalty=generation_penalty,
    )
