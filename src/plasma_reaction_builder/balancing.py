from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, List

from .catalog import TemplateCatalog
from .formula import composition_to_formula, parse_formula, parse_species_token, subtract_compositions
from .model import DiagnosticEntry, MissingProductSpec, ReactionTemplate, SpeciesPrototype
from .provenance import EvidenceRecord


@dataclass(slots=True)
class TemplateResolutionOutcome:
    template: ReactionTemplate
    diagnostics: List[DiagnosticEntry]


class BalanceResolver:
    def __init__(self, catalog: TemplateCatalog) -> None:
        self.catalog = catalog

    def _formula_balance_candidate(self, template: ReactionTemplate) -> tuple[str, int]:
        lhs_comp: Dict[str, int] = {}
        lhs_charge = 0
        for token in template.lhs_tokens:
            parsed = parse_species_token(token)
            lhs_charge += parsed.charge
            if parsed.formula:
                for el, count in parse_formula(parsed.formula).items():
                    lhs_comp[el] = lhs_comp.get(el, 0) + count

        rhs_comp: Dict[str, int] = {}
        rhs_charge = 0
        for token in template.rhs_tokens:
            parsed = parse_species_token(token)
            rhs_charge += parsed.charge
            if parsed.formula:
                for el, count in parse_formula(parsed.formula).items():
                    rhs_comp[el] = rhs_comp.get(el, 0) + count

        remaining_comp = subtract_compositions(lhs_comp, rhs_comp)
        if remaining_comp is None:
            raise ValueError(f"Mass balance resolution failed for template {template.key}")
        return composition_to_formula(remaining_comp), lhs_charge - rhs_charge

    def _rank_candidates(self, formula: str, charge: int, spec: MissingProductSpec) -> List[SpeciesPrototype]:
        out: List[SpeciesPrototype] = []
        for proto in self.catalog.species_library.values():
            if proto.formula != formula or proto.charge != charge:
                continue
            if proto.key in spec.disallow_keys:
                continue
            if spec.allowed_state_classes and proto.state_class not in spec.allowed_state_classes:
                continue
            if spec.allowed_tags and not set(spec.allowed_tags).intersection(proto.tags):
                continue
            out.append(proto)

        def rank(proto: SpeciesPrototype) -> tuple[int, int, int, str]:
            return (
                len(set(spec.allowed_tags).intersection(proto.tags)),
                1 if "curated" in proto.tags else 0,
                1 if proto.state_class in spec.allowed_state_classes else 0,
                proto.key,
            )

        return sorted(out, key=rank, reverse=True)

    @staticmethod
    def _token_from_species(proto: SpeciesPrototype) -> str:
        token = proto.formula
        if proto.charge > 0:
            token += "+" * proto.charge
        elif proto.charge < 0:
            token += "-" * abs(proto.charge)
        if proto.excitation_label:
            token += f"({proto.excitation_label})"
        return token

    def resolve(self, template: ReactionTemplate) -> TemplateResolutionOutcome:
        if not template.missing_products:
            return TemplateResolutionOutcome(template=template, diagnostics=[])

        resolved = replace(
            template,
            products=list(template.products),
            rhs_tokens=list(template.rhs_tokens),
            evidence=list(template.evidence),
        )
        diagnostics: List[DiagnosticEntry] = []

        for index, spec in enumerate(template.missing_products, start=1):
            if spec.kind != "mass_balance_neutral":
                raise NotImplementedError(f"Unsupported missing product kind: {spec.kind}")
            formula, charge = self._formula_balance_candidate(resolved)
            candidates = self._rank_candidates(formula, charge, spec)
            if candidates:
                chosen = candidates[0]
            else:
                key = formula + ("+" * charge if charge > 0 else "-" * abs(charge) if charge < 0 else "")
                state_class = "cation" if charge > 0 else "anion" if charge < 0 else "ground"
                chosen = self.catalog.ensure_species(key=key, formula=formula, charge=charge, state_class=state_class)

            resolved.products.append(chosen.key)
            resolved.rhs_tokens.append(self._token_from_species(chosen))
            resolved.evidence.append(
                EvidenceRecord(
                    source_system="inference",
                    source_name="mass_balance_completion",
                    acquisition_method="package_template",
                    evidence_kind="mass_balance_completion",
                    support_score=0.44,
                    locator=f"{template.key}::missing{index}",
                    note=f"Missing co-product completed by exact atom/charge balance: {chosen.key}.",
                )
            )
            diagnostics.append(
                DiagnosticEntry(
                    level="info",
                    code="mass_balance_completion",
                    message=f"Resolved missing co-product for {template.key}: {chosen.key}",
                    context={"template_key": template.key, "resolved_species_key": chosen.key},
                )
            )

        resolved.inferred_balance = False
        if resolved.note:
            resolved.note += " | Missing co-products completed by exact balance."
        else:
            resolved.note = "Missing co-products completed by exact balance."
        return TemplateResolutionOutcome(template=resolved, diagnostics=diagnostics)
