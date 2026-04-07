from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence
import csv
import json

from ..catalog import TemplateCatalog
from ..config import BuildConfig, load_config
from ..runtime import build_catalog

ViewRenderer = Callable[["VisualizationContext"], List["FigureArtifact"]]


@dataclass(slots=True)
class FigureArtifact:
    view_id: str
    audience: str
    kind: str
    path: str
    title: str
    description: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "view_id": self.view_id,
            "audience": self.audience,
            "kind": self.kind,
            "path": self.path,
            "title": self.title,
            "description": self.description,
        }


@dataclass(slots=True)
class ViewSpec:
    view_id: str
    title: str
    audience: str
    description: str
    tags: List[str]
    renderer: ViewRenderer
    requires_network: bool = False
    requires_catalog: bool = False


@dataclass(slots=True)
class NetworkSnapshot:
    payload: Dict[str, Any]
    metadata: Dict[str, Any]
    species: List[Dict[str, Any]]
    reactions: List[Dict[str, Any]]
    diagnostics: List[Dict[str, Any]]
    species_by_id: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    species_by_key: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    @classmethod
    def from_path(cls, path: str | Path) -> "NetworkSnapshot":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        species = list(payload.get("species", []))
        reactions = list(payload.get("reactions", []))
        species_by_id = {entry["id"]: entry for entry in species}
        species_by_key: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for entry in species:
            species_by_key[entry["prototype_key"]].append(entry)
        return cls(
            payload=payload,
            metadata=dict(payload.get("metadata", {})),
            species=species,
            reactions=reactions,
            diagnostics=list(payload.get("diagnostics", [])),
            species_by_id=species_by_id,
            species_by_key=dict(species_by_key),
        )


@dataclass(slots=True)
class VisualizationContext:
    output_dir: Path
    network: Optional[NetworkSnapshot] = None
    catalog: Optional[TemplateCatalog] = None
    config: Optional[BuildConfig] = None
    dpi: int = 180
    max_reactions_in_graph: int = 80

    @property
    def feed_keys(self) -> set[str]:
        if not self.config:
            return set()
        return {feed.species_key for feed in self.config.feeds}

    def artifact_path(self, relative_path: str) -> Path:
        path = self.output_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


_VIEW_REGISTRY: Dict[str, ViewSpec] = {}


def register_view(
    view_id: str,
    *,
    title: str,
    audience: str,
    description: str,
    tags: Sequence[str],
    requires_network: bool = False,
    requires_catalog: bool = False,
) -> Callable[[ViewRenderer], ViewRenderer]:
    def decorator(func: ViewRenderer) -> ViewRenderer:
        _VIEW_REGISTRY[view_id] = ViewSpec(
            view_id=view_id,
            title=title,
            audience=audience,
            description=description,
            tags=list(tags),
            renderer=func,
            requires_network=requires_network,
            requires_catalog=requires_catalog,
        )
        return func

    return decorator


def get_view_registry() -> Dict[str, ViewSpec]:
    return dict(_VIEW_REGISTRY)


def select_views(names: Sequence[str] | None = None) -> List[ViewSpec]:
    if not names:
        names = ["all"]
    normalized = {name.strip().lower() for name in names if name and name.strip()}
    if not normalized or "all" in normalized:
        return [spec for _, spec in sorted(_VIEW_REGISTRY.items())]
    selected: List[ViewSpec] = []
    for _, spec in sorted(_VIEW_REGISTRY.items()):
        if spec.view_id in normalized or spec.audience in normalized or normalized.intersection(set(spec.tags)):
            selected.append(spec)
    if not selected:
        raise ValueError(f"No visualization views matched: {sorted(normalized)}")
    return selected


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name) for name in fieldnames})


def write_manifest(output_dir: Path, artifacts: Sequence[FigureArtifact], *, network_path: Optional[str], config_path: Optional[str]) -> Path:
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "network_path": network_path,
        "config_path": config_path,
        "artifact_count": len(artifacts),
        "artifacts": [artifact.as_dict() for artifact in artifacts],
    }
    target = output_dir / "visual_manifest.json"
    target.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def load_catalog_from_config(config: BuildConfig | None) -> Optional[TemplateCatalog]:
    if config is None:
        return None
    return build_catalog(config)


def build_context(
    *,
    network_path: Optional[str],
    config_path: Optional[str],
    output_dir: str | Path,
    dpi: int = 180,
    max_reactions_in_graph: int = 80,
) -> VisualizationContext:
    config = load_config(config_path) if config_path else None
    catalog = load_catalog_from_config(config)
    network = NetworkSnapshot.from_path(network_path) if network_path else None
    ctx = VisualizationContext(
        output_dir=Path(output_dir).resolve(),
        network=network,
        catalog=catalog,
        config=config,
        dpi=dpi,
        max_reactions_in_graph=max_reactions_in_graph,
    )
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    return ctx


def render_visualizations(
    *,
    network_path: Optional[str],
    config_path: Optional[str],
    output_dir: str | Path,
    views: Sequence[str] | None = None,
    dpi: int = 180,
    max_reactions_in_graph: int = 80,
) -> List[FigureArtifact]:
    # Import side effects register the view functions.
    from . import network_views as _network_views  # noqa: F401
    from . import table_views as _table_views  # noqa: F401

    ctx = build_context(
        network_path=network_path,
        config_path=config_path,
        output_dir=output_dir,
        dpi=dpi,
        max_reactions_in_graph=max_reactions_in_graph,
    )
    artifacts: List[FigureArtifact] = []
    for spec in select_views(views):
        if spec.requires_network and ctx.network is None:
            continue
        if spec.requires_catalog and ctx.catalog is None:
            continue
        artifacts.extend(spec.renderer(ctx))
    write_manifest(ctx.output_dir, artifacts, network_path=network_path, config_path=config_path)
    return artifacts
