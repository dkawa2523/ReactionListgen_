from __future__ import annotations

from collections import Counter, defaultdict
from math import sqrt
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import networkx as nx

from .core import FigureArtifact, VisualizationContext, register_view
from .utils import (
    CATEGORY_COLORS,
    aggregate_species,
    build_generation_lanes,
    lane_positions,
    legend_from_categories,
    legend_from_families,
    reaction_family_colors,
    save_figure,
    short_family,
    state_category,
    truncate_text,
    wrap_label,
)


def _reaction_confidence(reaction: Dict[str, Any]) -> float:
    confidence = reaction.get("confidence") or {}
    return float(confidence.get("final_score", reaction.get("base_confidence", 0.0) or 0.0))


def _species_confidence(state: Dict[str, Any]) -> float:
    confidence = state.get("confidence") or {}
    return float(confidence.get("final_score", 0.0) or 0.0)


@register_view(
    "engineer_process_dag",
    title="Semiconductor engineer: process-fragment DAG",
    audience="engineer",
    description="Aggregated species DAG grouped by prototype key, with generation lanes and fragment roles.",
    tags=["network", "engineer"],
    requires_network=True,
)
def render_engineer_process_dag(ctx: VisualizationContext) -> List[FigureArtifact]:
    assert ctx.network is not None
    nodes, edges = aggregate_species(ctx.network.payload, feed_keys=ctx.feed_keys)
    if not nodes:
        return []

    graph = nx.DiGraph()
    for node in nodes:
        graph.add_node(node["prototype_key"], **node)
    for edge in edges:
        graph.add_edge(edge["source"], edge["target"], **edge)

    lanes = build_generation_lanes(
        nodes,
        generation_key="min_generation",
        sort_key=lambda entry: (
            entry.get("category", "neutral"),
            -entry.get("out_degree", 0),
            entry.get("display_name", ""),
        ),
    )
    positions: Dict[str, tuple[float, float]] = {}
    for generation, entries in sorted(lanes.items()):
        labels = [entry["prototype_key"] for entry in entries]
        positions.update(lane_positions(labels, x_value=float(generation), y_step=1.4))

    fig, ax = plt.subplots(figsize=(18, 10))
    ax.set_title("Semiconductor engineer view: gas decomposition / fragment DAG", fontsize=16, pad=16)
    ax.text(
        0.01,
        1.02,
        f"species={len(nodes)} aggregated, reactions={len(ctx.network.reactions)}, feeds={', '.join(sorted(ctx.feed_keys)) or 'n/a'}",
        transform=ax.transAxes,
        fontsize=10,
        color="#555555",
    )

    edge_widths = [1.2 + 0.8 * sqrt(graph.edges[edge].get("weight", 1)) for edge in graph.edges()]
    nx.draw_networkx_edges(
        graph,
        positions,
        ax=ax,
        arrows=True,
        arrowstyle="-|>",
        arrowsize=14,
        edge_color="#8899aa",
        width=edge_widths,
        alpha=0.8,
        connectionstyle="arc3,rad=0.04",
    )

    categories = sorted({data.get("category", "neutral") for _, data in graph.nodes(data=True)})
    for category in categories:
        members = [name for name, data in graph.nodes(data=True) if data.get("category") == category]
        if not members:
            continue
        nx.draw_networkx_nodes(
            graph,
            positions,
            nodelist=members,
            node_color=CATEGORY_COLORS.get(category, CATEGORY_COLORS["neutral"]),
            node_size=[700 + 140 * graph.nodes[name].get("out_degree", 0) for name in members],
            edgecolors="#333333",
            linewidths=1.0,
            ax=ax,
        )
    labels = {name: wrap_label(graph.nodes[name].get("display_name") or name, width=12) for name in graph.nodes}
    nx.draw_networkx_labels(graph, positions, labels=labels, font_size=8, ax=ax)

    for generation in sorted(lanes):
        ax.axvline(generation, linestyle="--", linewidth=0.7, color="#dddddd", zorder=0)
        ax.text(generation, 0.98, f"gen {generation}", transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=9)

    legend_from_categories(ax, categories)
    ax.set_axis_off()

    path = ctx.artifact_path("network/engineer_process_dag.png")
    save_figure(fig, path, dpi=ctx.dpi)
    return [
        FigureArtifact(
            view_id="engineer_process_dag",
            audience="engineer",
            kind="figure",
            path=str(path.relative_to(ctx.output_dir)),
            title="Semiconductor engineer: process-fragment DAG",
            description="Generation-layered DAG that shows how feed gases decompose into radicals, ions, excited states, and follow-up fragments.",
        )
    ]


@register_view(
    "engineer_inventory_summary",
    title="Semiconductor engineer: inventory summary",
    audience="engineer",
    description="Counts of generated state roles, reaction families, and hub fragments.",
    tags=["summary", "engineer"],
    requires_network=True,
)
def render_engineer_inventory_summary(ctx: VisualizationContext) -> List[FigureArtifact]:
    assert ctx.network is not None
    species = ctx.network.species
    reactions = ctx.network.reactions
    role_counts = Counter(state_category(state, feed_keys=ctx.feed_keys) for state in species)
    family_counts = Counter(reaction.get("family", "unknown") for reaction in reactions)
    hub_counts: Counter[str] = Counter()
    for reaction in reactions:
        for key in reaction.get("reactant_keys") or []:
            hub_counts[key] += 1
    top_hubs = hub_counts.most_common(8)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.8))
    axes[0].bar(role_counts.keys(), role_counts.values(), color=[CATEGORY_COLORS.get(name, "#888888") for name in role_counts.keys()])
    axes[0].set_title("generated state roles")
    axes[0].tick_params(axis="x", rotation=35)

    family_palette = reaction_family_colors(list(family_counts.keys()))
    axes[1].barh(list(family_counts.keys()), list(family_counts.values()), color=[family_palette[name] for name in family_counts.keys()])
    axes[1].set_title("reaction family count")

    if top_hubs:
        hub_names = [name for name, _ in top_hubs]
        hub_values = [count for _, count in top_hubs]
        axes[2].barh(hub_names, hub_values, color="#6c8ebf")
    axes[2].set_title("top reactant hubs")
    fig.suptitle("Semiconductor engineer view: generated inventory at a glance", fontsize=15)

    path = ctx.artifact_path("network/engineer_inventory_summary.png")
    save_figure(fig, path, dpi=ctx.dpi)
    return [
        FigureArtifact(
            view_id="engineer_inventory_summary",
            audience="engineer",
            kind="figure",
            path=str(path.relative_to(ctx.output_dir)),
            title="Semiconductor engineer: inventory summary",
            description="Compact summary of generated state roles, reaction families, and the fragments that act as the main branching hubs.",
        )
    ]


@register_view(
    "plasma_bipartite_dag",
    title="Plasma physicist: species-reaction DAG",
    audience="plasma",
    description="Detailed bipartite DAG that keeps reaction nodes explicit and colors them by family.",
    tags=["network", "plasma"],
    requires_network=True,
)
def render_plasma_bipartite_dag(ctx: VisualizationContext) -> List[FigureArtifact]:
    assert ctx.network is not None
    network = ctx.network
    reactions = sorted(network.reactions, key=lambda item: (-_reaction_confidence(item), item.get("generation", 0), item.get("family", "")))
    if len(reactions) > ctx.max_reactions_in_graph:
        reactions = reactions[: ctx.max_reactions_in_graph]
    included_reaction_ids = {reaction["id"] for reaction in reactions}
    included_species_ids = set()
    for reaction in reactions:
        included_species_ids.update(reaction.get("reactant_state_ids") or [])
        included_species_ids.update(reaction.get("product_state_ids") or [])
    species = [network.species_by_id[state_id] for state_id in included_species_ids if state_id in network.species_by_id]
    species = sorted(species, key=lambda item: (item.get("generation", 0), item.get("prototype_key", ""), item.get("display_name", "")))

    graph = nx.DiGraph()
    for state in species:
        graph.add_node(
            state["id"],
            node_type="state",
            generation=state.get("generation", 0),
            label=state.get("display_name") or state.get("prototype_key"),
            category=state_category(state, feed_keys=ctx.feed_keys),
        )
    for reaction in reactions:
        reaction_id = f"reaction::{reaction['id']}"
        graph.add_node(
            reaction_id,
            node_type="reaction",
            generation=reaction.get("generation", 0),
            label=short_family(reaction.get("family", "unknown")),
            family=reaction.get("family", "unknown"),
            confidence=_reaction_confidence(reaction),
        )
        for state_id in reaction.get("reactant_state_ids") or []:
            if state_id in included_species_ids:
                graph.add_edge(state_id, reaction_id)
        for state_id in reaction.get("product_state_ids") or []:
            if state_id in included_species_ids:
                graph.add_edge(reaction_id, state_id)

    positions: Dict[str, tuple[float, float]] = {}
    state_lanes = build_generation_lanes(
        [graph.nodes[node] | {"node_id": node} for node in graph.nodes if graph.nodes[node]["node_type"] == "state"],
        generation_key="generation",
        sort_key=lambda entry: (entry.get("category", "neutral"), entry.get("label", "")),
    )
    for generation, entries in sorted(state_lanes.items()):
        labels = [entry["node_id"] for entry in entries]
        positions.update(lane_positions(labels, x_value=float(generation), y_step=1.1))
    reaction_lanes = build_generation_lanes(
        [graph.nodes[node] | {"node_id": node} for node in graph.nodes if graph.nodes[node]["node_type"] == "reaction"],
        generation_key="generation",
        sort_key=lambda entry: (-entry.get("confidence", 0.0), entry.get("family", ""), entry.get("label", "")),
    )
    for generation, entries in sorted(reaction_lanes.items()):
        labels = [entry["node_id"] for entry in entries]
        positions.update(lane_positions(labels, x_value=float(generation) - 0.5, y_step=0.95))

    fig, ax = plt.subplots(figsize=(20, 11))
    ax.set_title("Plasma physicist view: species-reaction bipartite DAG", fontsize=16, pad=16)
    family_colors = reaction_family_colors([reaction.get("family", "unknown") for reaction in reactions])
    nx.draw_networkx_edges(graph, positions, ax=ax, arrows=True, arrowstyle="-|>", arrowsize=10, width=0.9, alpha=0.55, edge_color="#9aa3ad")

    categories = sorted({graph.nodes[node]["category"] for node in graph.nodes if graph.nodes[node]["node_type"] == "state"})
    for category in categories:
        members = [node for node in graph.nodes if graph.nodes[node]["node_type"] == "state" and graph.nodes[node]["category"] == category]
        nx.draw_networkx_nodes(
            graph,
            positions,
            nodelist=members,
            node_color=CATEGORY_COLORS.get(category, CATEGORY_COLORS["neutral"]),
            node_size=280,
            edgecolors="#333333",
            linewidths=0.7,
            ax=ax,
        )
    for family, color in family_colors.items():
        members = [node for node in graph.nodes if graph.nodes[node]["node_type"] == "reaction" and graph.nodes[node]["family"] == family]
        if not members:
            continue
        nx.draw_networkx_nodes(
            graph,
            positions,
            nodelist=members,
            node_color=color,
            node_shape="s",
            node_size=220,
            edgecolors="#222222",
            linewidths=0.6,
            ax=ax,
        )

    state_labels = {node: wrap_label(graph.nodes[node]["label"], width=10) for node in graph.nodes if graph.nodes[node]["node_type"] == "state"}
    reaction_labels = {node: graph.nodes[node]["label"] for node in graph.nodes if graph.nodes[node]["node_type"] == "reaction"}
    nx.draw_networkx_labels(graph, positions, labels=state_labels, font_size=7, ax=ax)
    nx.draw_networkx_labels(graph, positions, labels=reaction_labels, font_size=6.5, font_color="white", ax=ax)

    for generation in sorted(set(list(state_lanes.keys()) + list(reaction_lanes.keys()))):
        ax.axvline(float(generation), linestyle="--", linewidth=0.6, color="#dddddd", zorder=0)
        ax.text(float(generation), 0.98, f"state gen {generation}", transform=ax.get_xaxis_transform(), fontsize=9, ha="center", va="top")

    legend_from_categories(ax, categories)
    legend_from_families(ax, family_colors)
    ax.set_axis_off()

    subtitle = f"displayed reactions={len(reactions)} / total={len(network.reactions)}"
    ax.text(0.01, 1.02, subtitle, transform=ax.transAxes, fontsize=10, color="#555555")

    path = ctx.artifact_path("network/plasma_bipartite_dag.png")
    save_figure(fig, path, dpi=ctx.dpi)
    return [
        FigureArtifact(
            view_id="plasma_bipartite_dag",
            audience="plasma",
            kind="figure",
            path=str(path.relative_to(ctx.output_dir)),
            title="Plasma physicist: species-reaction DAG",
            description="Bipartite DAG that keeps reaction nodes explicit so charge-state creation, attachment, excitation, and fragmentation pathways remain visible.",
        )
    ]


@register_view(
    "plasma_threshold_map",
    title="Plasma physicist: threshold map",
    audience="plasma",
    description="Reaction thresholds and thermochemical annotations across generations.",
    tags=["summary", "plasma"],
    requires_network=True,
)
def render_plasma_threshold_map(ctx: VisualizationContext) -> List[FigureArtifact]:
    assert ctx.network is not None
    reactions = ctx.network.reactions
    families = [reaction.get("family", "unknown") for reaction in reactions]
    family_colors = reaction_family_colors(families)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for family in sorted(set(families)):
        subset = [reaction for reaction in reactions if reaction.get("family") == family]
        x_values = [reaction.get("generation", 0) for reaction in subset]
        y_values = [reaction.get("threshold_ev") if reaction.get("threshold_ev") is not None else -0.25 for reaction in subset]
        sizes = [60 + 100 * _reaction_confidence(reaction) for reaction in subset]
        axes[0].scatter(x_values, y_values, s=sizes, label=family, color=family_colors[family], alpha=0.8, edgecolors="#333333", linewidths=0.4)
    axes[0].axhline(0.0, color="#cccccc", linewidth=0.7)
    axes[0].set_xlabel("generation")
    axes[0].set_ylabel("threshold energy [eV] (N/A shown below 0)")
    axes[0].set_title("threshold ladder by reaction family")
    axes[0].legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False)

    delta_h_values = [reaction.get("delta_h_kj_mol") for reaction in reactions if reaction.get("delta_h_kj_mol") is not None]
    if delta_h_values:
        subset = [reaction for reaction in reactions if reaction.get("delta_h_kj_mol") is not None]
        x_values = [reaction.get("delta_h_kj_mol") for reaction in subset]
        y_values = [_reaction_confidence(reaction) for reaction in subset]
        colors = [family_colors[reaction.get("family", "unknown")] for reaction in subset]
        axes[1].scatter(x_values, y_values, s=90, color=colors, alpha=0.8, edgecolors="#333333", linewidths=0.4)
        axes[1].set_xlabel("ΔH [kJ/mol]")
        axes[1].set_ylabel("confidence")
        axes[1].set_title("thermochemical annotation vs confidence")
    else:
        axes[1].axis("off")
        axes[1].text(0.02, 0.92, "No ΔH annotations were present in this network.", fontsize=12, va="top")

    fig.suptitle("Plasma physicist view: energetics / annotation map", fontsize=15)
    path = ctx.artifact_path("network/plasma_threshold_map.png")
    save_figure(fig, path, dpi=ctx.dpi)
    return [
        FigureArtifact(
            view_id="plasma_threshold_map",
            audience="plasma",
            kind="figure",
            path=str(path.relative_to(ctx.output_dir)),
            title="Plasma physicist: threshold map",
            description="Scatter summary of reaction thresholds, generations, thermochemical annotations, and confidence values.",
        )
    ]


@register_view(
    "datasci_dataset_summary",
    title="Data scientist: dataset summary",
    audience="datasci",
    description="Coverage, provenance, confidence, and family-count dashboard for the generated network.",
    tags=["summary", "datasci", "data"],
    requires_network=True,
)
def render_datasci_dataset_summary(ctx: VisualizationContext) -> List[FigureArtifact]:
    assert ctx.network is not None
    network = ctx.network
    species = network.species
    reactions = network.reactions

    source_counts: Counter[str] = Counter()
    for state in species:
        for evidence in state.get("evidence") or []:
            source_counts[evidence.get("source_name") or evidence.get("source_system") or "unknown"] += 1
    for reaction in reactions:
        for evidence in reaction.get("evidence") or []:
            source_counts[evidence.get("source_name") or evidence.get("source_system") or "unknown"] += 1

    species_tiers = Counter((state.get("confidence") or {}).get("tier", "unknown") for state in species)
    reaction_tiers = Counter((reaction.get("confidence") or {}).get("tier", "unknown") for reaction in reactions)
    family_counts = Counter(reaction.get("family", "unknown") for reaction in reactions)

    field_coverage = {
        "species.identity": sum(1 for state in species if state.get("identity")),
        "species.thermo": sum(1 for state in species if (state.get("thermo") or {}).get("delta_hf_298_kj_mol") is not None),
        "species.evidence": sum(1 for state in species if state.get("evidence")),
        "reaction.threshold": sum(1 for reaction in reactions if reaction.get("threshold_ev") is not None),
        "reaction.delta_h": sum(1 for reaction in reactions if reaction.get("delta_h_kj_mol") is not None),
        "reaction.evidence": sum(1 for reaction in reactions if reaction.get("evidence")),
    }
    denominators = {
        "species.identity": len(species),
        "species.thermo": len(species),
        "species.evidence": len(species),
        "reaction.threshold": len(reactions),
        "reaction.delta_h": len(reactions),
        "reaction.evidence": len(reactions),
    }

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    axes[0, 0].barh(list(source_counts.keys()), list(source_counts.values()), color="#6c8ebf")
    axes[0, 0].set_title("evidence source mentions")

    coverage_names = list(field_coverage.keys())
    coverage_values = [100.0 * field_coverage[name] / max(1, denominators[name]) for name in coverage_names]
    axes[0, 1].barh(coverage_names, coverage_values, color="#82b366")
    axes[0, 1].set_xlim(0, 100)
    axes[0, 1].set_title("field coverage [%]")

    tier_names = sorted(set(list(species_tiers.keys()) + list(reaction_tiers.keys())))
    tier_x = range(len(tier_names))
    axes[1, 0].bar([index - 0.18 for index in tier_x], [species_tiers.get(name, 0) for name in tier_names], width=0.36, label="species", color="#9673a6")
    axes[1, 0].bar([index + 0.18 for index in tier_x], [reaction_tiers.get(name, 0) for name in tier_names], width=0.36, label="reactions", color="#f6b26b")
    axes[1, 0].set_xticks(list(tier_x), tier_names)
    axes[1, 0].set_title("confidence tier counts")
    axes[1, 0].legend(frameon=False)

    family_palette = reaction_family_colors(list(family_counts.keys()))
    axes[1, 1].barh(list(family_counts.keys()), list(family_counts.values()), color=[family_palette[name] for name in family_counts.keys()])
    axes[1, 1].set_title("reaction family counts")

    fig.suptitle("Data scientist view: generated dataset health / provenance summary", fontsize=15)
    path = ctx.artifact_path("network/datasci_dataset_summary.png")
    save_figure(fig, path, dpi=ctx.dpi)
    return [
        FigureArtifact(
            view_id="datasci_dataset_summary",
            audience="datasci",
            kind="figure",
            path=str(path.relative_to(ctx.output_dir)),
            title="Data scientist: dataset summary",
            description="Coverage and provenance dashboard for the generated state / reaction network, including evidence counts, field completeness, confidence tiers, and family counts.",
        )
    ]
