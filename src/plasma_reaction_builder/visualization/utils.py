from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple
import math
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


CATEGORY_COLORS = {
    "feed": "#d4a72c",
    "cation": "#c94f4f",
    "anion": "#4f81bd",
    "excited": "#8e63ce",
    "radical": "#4f9d69",
    "atom": "#8a5a44",
    "neutral": "#7f8c8d",
}


def save_figure(fig: plt.Figure, path: Path, dpi: int = 180) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


FAMILY_SHORT = {
    "electron_attachment": "EA",
    "electron_dissociative_ionization": "EDI",
    "electron_dissociation": "ED",
    "electron_excitation": "EE",
    "electron_excitation_vibrational": "EEV",
    "electron_ionization": "EI",
    "electron_deexcitation": "EDE",
    "electron_collision_evidence": "ECE",
    "gas_phase_evidence": "GPE",
    "ion_fragmentation": "IF",
    "ion_neutral_followup": "INF",
    "neutral_fragmentation": "NF",
    "radiative_relaxation": "RR",
    "radical_fragmentation": "RF",
    "collisional_quenching": "CQ",
    "superelastic_deexcitation": "SED",
}


def reaction_family_colors(families: Sequence[str]) -> Dict[str, str]:
    cmap = plt.get_cmap("tab20")
    unique = sorted(dict.fromkeys(families))
    return {family: matplotlib.colors.to_hex(cmap(index % 20)) for index, family in enumerate(unique)}


def short_family(family: str) -> str:
    return FAMILY_SHORT.get(family, family[:6].upper())


def truncate_text(value: Any, max_len: int = 34) -> str:
    text = "" if value is None else str(value)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def wrap_label(value: Any, width: int = 14) -> str:
    text = "" if value is None else str(value)
    return "\n".join(textwrap.wrap(text, width=width)) or text


def state_category(state: Dict[str, Any], *, feed_keys: set[str]) -> str:
    prototype_key = state.get("prototype_key")
    if prototype_key in feed_keys:
        return "feed"
    charge = int(state.get("charge", 0))
    state_class = state.get("state_class")
    tags = set(state.get("tags") or [])
    if charge > 0:
        return "cation"
    if charge < 0:
        return "anion"
    if state_class == "excited" or state.get("excitation_label") or state.get("excitation_energy_ev") is not None:
        return "excited"
    if "radical" in tags:
        return "radical"
    if state_class == "atom":
        return "atom"
    return "neutral"


def aggregate_species(network: Dict[str, Any], *, feed_keys: set[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    species = list(network.get("species", []))
    reactions = list(network.get("reactions", []))
    grouped: Dict[str, Dict[str, Any]] = {}
    for state in species:
        key = state["prototype_key"]
        entry = grouped.setdefault(
            key,
            {
                "prototype_key": key,
                "display_name": state.get("display_name") or key,
                "formula": state.get("formula"),
                "min_generation": state.get("generation", 0),
                "categories": Counter(),
                "charges": Counter(),
                "state_count": 0,
                "out_degree": 0,
                "in_degree": 0,
                "tags": Counter(),
            },
        )
        entry["state_count"] += 1
        entry["min_generation"] = min(entry["min_generation"], state.get("generation", 0))
        entry["categories"][state_category(state, feed_keys=feed_keys)] += 1
        entry["charges"][int(state.get("charge", 0))] += 1
        for tag in state.get("tags") or []:
            entry["tags"][tag] += 1
    edge_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for reaction in reactions:
        reactants = reaction.get("reactant_keys") or []
        products = reaction.get("product_keys") or []
        for src in reactants:
            for dst in products:
                if src == dst:
                    continue
                key = (src, dst)
                record = edge_map.setdefault(
                    key,
                    {
                        "source": src,
                        "target": dst,
                        "weight": 0,
                        "families": Counter(),
                        "generations": Counter(),
                    },
                )
                record["weight"] += 1
                record["families"][reaction.get("family") or "unknown"] += 1
                record["generations"][reaction.get("generation") or 0] += 1
                if src in grouped:
                    grouped[src]["out_degree"] += 1
                if dst in grouped:
                    grouped[dst]["in_degree"] += 1
    nodes: List[Dict[str, Any]] = []
    for entry in grouped.values():
        category = entry["categories"].most_common(1)[0][0] if entry["categories"] else "neutral"
        entry["category"] = category
        entry["label"] = entry["display_name"]
        nodes.append(entry)
    edges = list(edge_map.values())
    return nodes, edges


def lane_positions(labels: Sequence[str], x_value: float, y_start: float = 0.0, y_step: float = 1.0) -> Dict[str, Tuple[float, float]]:
    if not labels:
        return {}
    centered_start = y_start - (len(labels) - 1) * y_step / 2.0
    return {label: (x_value, centered_start + index * y_step) for index, label in enumerate(labels)}


def build_generation_lanes(items: Sequence[Dict[str, Any]], generation_key: str, sort_key: Callable[[Dict[str, Any]], Any]) -> Dict[Any, List[Dict[str, Any]]]:
    grouped: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[item.get(generation_key, 0)].append(item)
    for generation, entries in grouped.items():
        grouped[generation] = sorted(entries, key=sort_key)
    return dict(grouped)


def legend_from_categories(ax: plt.Axes, categories: Sequence[str]) -> None:
    handles = [Patch(facecolor=CATEGORY_COLORS[category], edgecolor="#333333", label=category) for category in categories if category in CATEGORY_COLORS]
    if handles:
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, title="species role")


def legend_from_families(ax: plt.Axes, family_colors: Dict[str, str]) -> None:
    handles = [Line2D([0], [0], marker="s", linestyle="", color=color, label=family, markersize=9) for family, color in family_colors.items()]
    if handles:
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, title="reaction family")


def monospace_table_lines(rows: Sequence[Dict[str, Any]], columns: Sequence[Tuple[str, str, int]]) -> List[str]:
    header = " | ".join(title.ljust(width) for _, title, width in columns)
    divider = "-+-".join("-" * width for _, _, width in columns)
    lines = [header, divider]
    for row in rows:
        line = " | ".join(truncate_text(row.get(field, ""), max_len=width).ljust(width) for field, _, width in columns)
        lines.append(line)
    return lines


def render_text_pages(title: str, subtitle: str, rows: Sequence[Dict[str, Any]], columns: Sequence[Tuple[str, str, int]], base_path: Path, *, dpi: int, lines_per_page: int = 24) -> List[Path]:
    paths: List[Path] = []
    line_rows = [dict(row) for row in rows]
    pages = max(1, math.ceil(len(line_rows) / lines_per_page))
    for page_index in range(pages):
        page_rows = line_rows[page_index * lines_per_page : (page_index + 1) * lines_per_page]
        lines = monospace_table_lines(page_rows, columns)
        fig = plt.figure(figsize=(17, 10))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis("off")
        ax.text(0.02, 0.98, title, fontsize=16, fontweight="bold", va="top")
        ax.text(0.02, 0.945, f"{subtitle} | page {page_index + 1}/{pages}", fontsize=10, color="#555555", va="top")
        ax.text(0.02, 0.91, "\n".join(lines), family="monospace", fontsize=8.5, va="top")
        page_path = base_path.with_name(f"{base_path.stem}_p{page_index + 1:02d}{base_path.suffix}")
        save_figure(fig, page_path, dpi=dpi)
        paths.append(page_path)
    return paths
