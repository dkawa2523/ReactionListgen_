from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from collections import Counter

import matplotlib.pyplot as plt

from .core import FigureArtifact, VisualizationContext, register_view, write_csv
from .utils import CATEGORY_COLORS, reaction_family_colors, render_text_pages, save_figure, truncate_text


def _evidence_sources(entry: Dict[str, Any]) -> str:
    sources = []
    for evidence in entry.get("evidence") or []:
        name = evidence.get("source_name") or evidence.get("source_system")
        if name and name not in sources:
            sources.append(name)
    return ", ".join(sources)


def _confidence_value(entry: Dict[str, Any]) -> str:
    confidence = entry.get("confidence") or {}
    value = confidence.get("final_score")
    if value is None:
        return ""
    return f"{float(value):.3f}"


def _metadata_value(entry: Dict[str, Any], key: str) -> str:
    metadata = entry.get("metadata") or {}
    value = metadata.get(key)
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item)
    return str(value)


def _write_generated_species_csv(ctx: VisualizationContext) -> Path:
    assert ctx.network is not None
    rows: List[Dict[str, Any]] = []
    for state in sorted(ctx.network.species, key=lambda item: (item.get("generation", 0), item.get("prototype_key", ""), item.get("display_name", ""))):
        rows.append(
            {
                "generation": state.get("generation"),
                "prototype_key": state.get("prototype_key"),
                "display_name": state.get("display_name"),
                "formula": state.get("formula"),
                "charge": state.get("charge"),
                "state_class": state.get("state_class"),
                "excitation_label": state.get("excitation_label"),
                "tags": ", ".join(state.get("tags") or []),
                "confidence": _confidence_value(state),
                "evidence_sources": _evidence_sources(state),
                "origin": _metadata_value(state, "state_origin"),
            }
        )
    path = ctx.artifact_path("lists/generated_species.csv")
    write_csv(path, rows, fieldnames=list(rows[0].keys()) if rows else ["generation", "prototype_key", "display_name", "formula", "charge", "state_class", "excitation_label", "tags", "confidence", "evidence_sources", "origin"])
    return path


def _write_generated_reactions_csv(ctx: VisualizationContext) -> Path:
    assert ctx.network is not None
    rows: List[Dict[str, Any]] = []
    for reaction in sorted(ctx.network.reactions, key=lambda item: (item.get("generation", 0), item.get("family", ""), item.get("equation", ""))):
        rows.append(
            {
                "generation": reaction.get("generation"),
                "family": reaction.get("family"),
                "equation": reaction.get("equation"),
                "threshold_ev": reaction.get("threshold_ev"),
                "delta_h_kj_mol": reaction.get("delta_h_kj_mol"),
                "confidence": _confidence_value(reaction),
                "evidence_sources": _evidence_sources(reaction),
                "origin": _metadata_value(reaction, "template_origin"),
                "source_system": _metadata_value(reaction, "template_source_system"),
                "catalog_resource": _metadata_value(reaction, "catalog_resource"),
                "note": reaction.get("note"),
            }
        )
    path = ctx.artifact_path("lists/generated_reactions.csv")
    write_csv(path, rows, fieldnames=list(rows[0].keys()) if rows else ["generation", "family", "equation", "threshold_ev", "delta_h_kj_mol", "confidence", "evidence_sources", "origin", "source_system", "catalog_resource", "note"])
    return path


def _write_dictionary_species_csv(ctx: VisualizationContext) -> Path:
    assert ctx.catalog is not None
    rows: List[Dict[str, Any]] = []
    for key, proto in sorted(ctx.catalog.species_library.items()):
        rows.append(
            {
                "key": proto.key,
                "display_name": proto.display_name,
                "formula": proto.formula,
                "charge": proto.charge,
                "state_class": proto.state_class,
                "excitation_label": proto.excitation_label,
                "tags": ", ".join(proto.tags),
                "aliases": ", ".join(proto.aliases),
                "origin": str(proto.metadata.get("state_origin") or ""),
                "catalog_resource": str(proto.metadata.get("catalog_resource") or ""),
            }
        )
    path = ctx.artifact_path("lists/dictionary_species.csv")
    write_csv(path, rows, fieldnames=list(rows[0].keys()) if rows else ["key", "display_name", "formula", "charge", "state_class", "excitation_label", "tags", "aliases", "origin", "catalog_resource"])
    return path


def _write_dictionary_reaction_csv(ctx: VisualizationContext) -> Path:
    assert ctx.catalog is not None
    rows: List[Dict[str, Any]] = []
    for template in sorted(ctx.catalog.templates, key=lambda item: (item.family, item.key)):
        rows.append(
            {
                "key": template.key,
                "family": template.family,
                "projectile": template.required_projectile,
                "reactants": ", ".join(template.reactants),
                "products": ", ".join(template.products),
                "equation": template.equation(),
                "threshold_ev": template.threshold_ev,
                "reference_ids": ", ".join(template.reference_ids),
                "origin": str(template.metadata.get("template_origin") or ""),
                "layer": str(template.metadata.get("template_layer") or ""),
                "source_systems": ", ".join(template.metadata.get("reference_source_systems", []) or []),
                "catalog_resource": str(template.metadata.get("catalog_resource") or ""),
                "note": template.note,
            }
        )
    path = ctx.artifact_path("lists/dictionary_reaction_templates.csv")
    write_csv(path, rows, fieldnames=list(rows[0].keys()) if rows else ["key", "family", "projectile", "reactants", "products", "equation", "threshold_ev", "reference_ids", "origin", "layer", "source_systems", "catalog_resource", "note"])
    return path


@register_view(
    "generated_state_pages",
    title="Generated state list pages",
    audience="datasci",
    description="Paginated image tables for the generated state list, plus CSV export.",
    tags=["lists", "datasci", "generated", "state"],
    requires_network=True,
)
def render_generated_state_pages(ctx: VisualizationContext) -> List[FigureArtifact]:
    assert ctx.network is not None
    csv_path = _write_generated_species_csv(ctx)
    rows: List[Dict[str, Any]] = []
    for state in sorted(ctx.network.species, key=lambda item: (item.get("generation", 0), item.get("prototype_key", ""), item.get("display_name", ""))):
        rows.append(
            {
                "generation": state.get("generation"),
                "prototype_key": state.get("prototype_key"),
                "formula": state.get("formula"),
                "charge": state.get("charge"),
                "class": state.get("state_class"),
                "excitation": state.get("excitation_label") or "",
                "confidence": _confidence_value(state),
                "sources": _evidence_sources(state),
            }
        )
    columns = [
        ("generation", "gen", 4),
        ("prototype_key", "prototype_key", 20),
        ("formula", "formula", 10),
        ("charge", "q", 3),
        ("class", "class", 10),
        ("excitation", "exc", 12),
        ("confidence", "conf", 6),
        ("sources", "sources", 30),
    ]
    base_path = ctx.artifact_path("tables/generated_state_list.png")
    pages = render_text_pages(
        "Generated state list",
        f"current network species list | csv={csv_path.relative_to(ctx.output_dir)}",
        rows,
        columns,
        base_path,
        dpi=ctx.dpi,
    )
    artifacts = [
        FigureArtifact(
            view_id="generated_state_pages",
            audience="datasci",
            kind="csv",
            path=str(csv_path.relative_to(ctx.output_dir)),
            title="Generated state list CSV",
            description="Tabular export of the generated state list.",
        )
    ]
    artifacts.extend(
        FigureArtifact(
            view_id="generated_state_pages",
            audience="datasci",
            kind="figure",
            path=str(page.relative_to(ctx.output_dir)),
            title="Generated state list page",
            description="Paginated image table for the generated state list.",
        )
        for page in pages
    )
    return artifacts


@register_view(
    "generated_reaction_pages",
    title="Generated reaction list pages",
    audience="datasci",
    description="Paginated image tables for the generated reaction list, plus CSV export.",
    tags=["lists", "datasci", "generated", "reaction"],
    requires_network=True,
)
def render_generated_reaction_pages(ctx: VisualizationContext) -> List[FigureArtifact]:
    assert ctx.network is not None
    csv_path = _write_generated_reactions_csv(ctx)
    rows: List[Dict[str, Any]] = []
    for reaction in sorted(ctx.network.reactions, key=lambda item: (item.get("generation", 0), item.get("family", ""), item.get("equation", ""))):
        rows.append(
            {
                "generation": reaction.get("generation"),
                "family": reaction.get("family"),
                "equation": truncate_text(reaction.get("equation"), 42),
                "threshold": "" if reaction.get("threshold_ev") is None else f"{float(reaction['threshold_ev']):.2f}",
                "confidence": _confidence_value(reaction),
                "sources": _evidence_sources(reaction),
                "origin": _metadata_value(reaction, "template_origin"),
            }
        )
    columns = [
        ("generation", "gen", 4),
        ("family", "family", 18),
        ("equation", "equation", 42),
        ("threshold", "thr[eV]", 8),
        ("confidence", "conf", 6),
        ("sources", "sources", 26),
        ("origin", "origin", 14),
    ]
    base_path = ctx.artifact_path("tables/generated_reaction_list.png")
    pages = render_text_pages(
        "Generated reaction list",
        f"current network reaction list | csv={csv_path.relative_to(ctx.output_dir)}",
        rows,
        columns,
        base_path,
        dpi=ctx.dpi,
    )
    artifacts = [
        FigureArtifact(
            view_id="generated_reaction_pages",
            audience="datasci",
            kind="csv",
            path=str(csv_path.relative_to(ctx.output_dir)),
            title="Generated reaction list CSV",
            description="Tabular export of the generated reaction list.",
        )
    ]
    artifacts.extend(
        FigureArtifact(
            view_id="generated_reaction_pages",
            audience="datasci",
            kind="figure",
            path=str(page.relative_to(ctx.output_dir)),
            title="Generated reaction list page",
            description="Paginated image table for the generated reaction list.",
        )
        for page in pages
    )
    return artifacts


@register_view(
    "dictionary_species_pages",
    title="State dictionary pages",
    audience="datasci",
    description="Paginated image tables for the current packaged state dictionary, plus CSV export.",
    tags=["lists", "datasci", "dictionary", "state"],
    requires_catalog=True,
)
def render_dictionary_species_pages(ctx: VisualizationContext) -> List[FigureArtifact]:
    assert ctx.catalog is not None
    csv_path = _write_dictionary_species_csv(ctx)
    rows: List[Dict[str, Any]] = []
    for key, proto in sorted(ctx.catalog.species_library.items()):
        rows.append(
            {
                "key": proto.key,
                "formula": proto.formula,
                "charge": proto.charge,
                "class": proto.state_class,
                "excitation": proto.excitation_label or "",
                "tags": ", ".join(proto.tags),
                "aliases": ", ".join(proto.aliases),
            }
        )
    columns = [
        ("key", "key", 20),
        ("formula", "formula", 10),
        ("charge", "q", 3),
        ("class", "class", 10),
        ("excitation", "exc", 12),
        ("tags", "tags", 28),
        ("aliases", "aliases", 24),
    ]
    base_path = ctx.artifact_path("tables/dictionary_species.png")
    pages = render_text_pages(
        "Packaged state dictionary",
        f"loaded resources={len(ctx.catalog.loaded_resources)} | csv={csv_path.relative_to(ctx.output_dir)}",
        rows,
        columns,
        base_path,
        dpi=ctx.dpi,
    )
    artifacts = [
        FigureArtifact(
            view_id="dictionary_species_pages",
            audience="datasci",
            kind="csv",
            path=str(csv_path.relative_to(ctx.output_dir)),
            title="State dictionary CSV",
            description="Tabular export of the current packaged state dictionary.",
        )
    ]
    artifacts.extend(
        FigureArtifact(
            view_id="dictionary_species_pages",
            audience="datasci",
            kind="figure",
            path=str(page.relative_to(ctx.output_dir)),
            title="State dictionary page",
            description="Paginated image table for the current packaged state dictionary.",
        )
        for page in pages
    )
    return artifacts


@register_view(
    "dictionary_reaction_pages",
    title="Reaction dictionary pages",
    audience="datasci",
    description="Paginated image tables for the current packaged reaction templates, plus CSV export.",
    tags=["lists", "datasci", "dictionary", "reaction"],
    requires_catalog=True,
)
def render_dictionary_reaction_pages(ctx: VisualizationContext) -> List[FigureArtifact]:
    assert ctx.catalog is not None
    csv_path = _write_dictionary_reaction_csv(ctx)
    rows: List[Dict[str, Any]] = []
    for template in sorted(ctx.catalog.templates, key=lambda item: (item.family, item.key)):
        rows.append(
            {
                "key": template.key,
                "family": template.family,
                "projectile": template.required_projectile or "",
                "equation": truncate_text(template.equation(), 44),
                "threshold": "" if template.threshold_ev is None else f"{float(template.threshold_ev):.2f}",
                "origin": str(template.metadata.get("template_origin") or ""),
                "refs": ", ".join(template.reference_ids),
            }
        )
    columns = [
        ("key", "key", 20),
        ("family", "family", 18),
        ("projectile", "proj", 6),
        ("equation", "equation", 44),
        ("threshold", "thr[eV]", 8),
        ("origin", "origin", 14),
        ("refs", "refs", 12),
    ]
    base_path = ctx.artifact_path("tables/dictionary_reaction_templates.png")
    pages = render_text_pages(
        "Packaged reaction template dictionary",
        f"loaded resources={len(ctx.catalog.loaded_resources)} | csv={csv_path.relative_to(ctx.output_dir)}",
        rows,
        columns,
        base_path,
        dpi=ctx.dpi,
    )
    artifacts = [
        FigureArtifact(
            view_id="dictionary_reaction_pages",
            audience="datasci",
            kind="csv",
            path=str(csv_path.relative_to(ctx.output_dir)),
            title="Reaction dictionary CSV",
            description="Tabular export of the current packaged reaction template dictionary.",
        )
    ]
    artifacts.extend(
        FigureArtifact(
            view_id="dictionary_reaction_pages",
            audience="datasci",
            kind="figure",
            path=str(page.relative_to(ctx.output_dir)),
            title="Reaction dictionary page",
            description="Paginated image table for the current packaged reaction template dictionary.",
        )
        for page in pages
    )
    return artifacts


@register_view(
    "dictionary_engineer_summary",
    title="Semiconductor engineer: current dictionary summary",
    audience="engineer",
    description="High-level summary of the packaged state and reaction dictionaries.",
    tags=["dictionary", "engineer", "summary"],
    requires_catalog=True,
)
def render_dictionary_engineer_summary(ctx: VisualizationContext) -> List[FigureArtifact]:
    assert ctx.catalog is not None
    role_counts: Counter[str] = Counter()
    for proto in ctx.catalog.species_library.values():
        if proto.charge > 0:
            role_counts["cation"] += 1
        elif proto.charge < 0:
            role_counts["anion"] += 1
        elif proto.state_class == "excited" or proto.excitation_label:
            role_counts["excited"] += 1
        elif "radical" in set(proto.tags):
            role_counts["radical"] += 1
        elif proto.state_class == "atom":
            role_counts["atom"] += 1
        else:
            role_counts["neutral"] += 1
    family_counts: Counter[str] = Counter(template.family for template in ctx.catalog.templates)
    projectile_counts: Counter[str] = Counter(template.required_projectile or "none" for template in ctx.catalog.templates)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.8))
    axes[0].bar(role_counts.keys(), role_counts.values(), color=[CATEGORY_COLORS.get(name, "#888888") for name in role_counts.keys()])
    axes[0].set_title("packaged state roles")
    axes[0].tick_params(axis="x", rotation=35)

    palette = reaction_family_colors(list(family_counts.keys()))
    axes[1].barh(list(family_counts.keys()), list(family_counts.values()), color=[palette[name] for name in family_counts.keys()])
    axes[1].set_title("template family count")

    axes[2].bar(projectile_counts.keys(), projectile_counts.values(), color="#6c8ebf")
    axes[2].set_title("projectile coverage")
    axes[2].tick_params(axis="x", rotation=35)
    fig.suptitle("Semiconductor engineer view: current packaged dictionary", fontsize=15)

    path = ctx.artifact_path("dictionary/engineer_dictionary_summary.png")
    save_figure(fig, path, dpi=ctx.dpi)
    return [FigureArtifact(
        view_id="dictionary_engineer_summary",
        audience="engineer",
        kind="figure",
        path=str(path.relative_to(ctx.output_dir)),
        title="Semiconductor engineer: current dictionary summary",
        description="Counts of packaged species roles, reaction families, and projectile coverage in the current dictionaries.",
    )]


@register_view(
    "dictionary_plasma_summary",
    title="Plasma physicist: current dictionary summary",
    audience="plasma",
    description="Charge / excitation composition and threshold coverage of the packaged dictionaries.",
    tags=["dictionary", "plasma", "summary"],
    requires_catalog=True,
)
def render_dictionary_plasma_summary(ctx: VisualizationContext) -> List[FigureArtifact]:
    assert ctx.catalog is not None
    charge_counts: Counter[str] = Counter()
    excited_count = 0
    for proto in ctx.catalog.species_library.values():
        charge_counts[str(proto.charge)] += 1
        if proto.state_class == "excited" or proto.excitation_label:
            excited_count += 1
    family_counts: Counter[str] = Counter()
    threshold_counts: Counter[str] = Counter()
    for template in ctx.catalog.templates:
        family_counts[template.family] += 1
        if template.threshold_ev is not None:
            threshold_counts[template.family] += 1

    family_names = list(family_counts.keys())
    threshold_pct = [100.0 * threshold_counts.get(name, 0) / max(1, family_counts[name]) for name in family_names]
    palette = reaction_family_colors(family_names)

    fig, axes = plt.subplots(1, 2, figsize=(16, 5.8))
    axes[0].bar(list(charge_counts.keys()) + ["excited"], list(charge_counts.values()) + [excited_count], color=["#6c8ebf", "#aaaaaa", "#c94f4f", "#8e63ce"][: len(charge_counts)+1])
    axes[0].set_title("state charge / excitation composition")

    axes[1].barh(family_names, threshold_pct, color=[palette[name] for name in family_names])
    axes[1].set_xlim(0, 100)
    axes[1].set_title("threshold annotation coverage [%]")
    fig.suptitle("Plasma physicist view: current packaged dictionary", fontsize=15)

    path = ctx.artifact_path("dictionary/plasma_dictionary_summary.png")
    save_figure(fig, path, dpi=ctx.dpi)
    return [FigureArtifact(
        view_id="dictionary_plasma_summary",
        audience="plasma",
        kind="figure",
        path=str(path.relative_to(ctx.output_dir)),
        title="Plasma physicist: current dictionary summary",
        description="Charge-state composition of the packaged state dictionary and threshold coverage in the packaged reaction template dictionary.",
    )]
