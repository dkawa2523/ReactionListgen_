from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .adapters import NistAsdBootstrapAdapter, QdbApiClient
from .config import load_config
from .network_manifest import build_network_manifest_from_payload
from .runtime import AppRuntime, build_runtime
from .runtime_audit import build_runtime_audit
from .source_ops import (
    build_catalog_manifest,
    build_evidence_manifest,
    build_pubchem_snapshot,
    build_source_lock,
    inspect_sources,
    load_json_if_exists,
    merge_evidence_payloads,
)
from .state_catalog import materialize_state_master_file
from .version import __version__
from .visualization import render_visualizations


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="plasma-rxn-builder")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build an evidence-annotated state/reaction network")
    build_parser.add_argument("config", help="Path to YAML configuration")
    build_parser.add_argument("--output", required=True, help="Output JSON path")
    build_parser.add_argument("--lock-output", help="Optional lock JSON path")
    build_parser.add_argument("--head-vamdc", action="store_true", help="Include VAMDC HEAD preflight in lock output")

    validate_parser = subparsers.add_parser("validate-config", help="Load configuration and report resolved paths")
    validate_parser.add_argument("config", help="Path to YAML configuration")

    collect_parser = subparsers.add_parser("collect-evidence", help="Collect reaction evidence from configured sources and write a normalized snapshot")
    collect_parser.add_argument("config", help="Path to YAML configuration")
    collect_parser.add_argument("--output", required=True, help="Output normalized JSON path")
    collect_parser.add_argument("--existing", help="Optional existing evidence snapshot to merge with")
    collect_parser.add_argument("--merge", action="store_true", help="Merge new records into the existing snapshot")
    collect_parser.add_argument("--lock-output", help="Optional lock JSON path")
    collect_parser.add_argument("--head-vamdc", action="store_true", help="Include VAMDC HEAD preflight in lock output")

    inspect_parser = subparsers.add_parser("inspect-sources", help="Inspect configured sources and report snapshot/live readiness")
    inspect_parser.add_argument("config", help="Path to YAML configuration")
    inspect_parser.add_argument("--output", help="Optional JSON report path")
    inspect_parser.add_argument("--head-vamdc", action="store_true", help="Run VAMDC HEAD preflight for live queries")

    write_lock_parser = subparsers.add_parser("write-lock", help="Write a reproducibility lock file for the current source configuration")
    write_lock_parser.add_argument("config", help="Path to YAML configuration")
    write_lock_parser.add_argument("--output", required=True, help="Output lock JSON path")
    write_lock_parser.add_argument("--head-vamdc", action="store_true", help="Run VAMDC HEAD preflight for live queries")

    freeze_pubchem_parser = subparsers.add_parser("freeze-pubchem", help="Resolve feed identities and write a PubChem snapshot JSON")
    freeze_pubchem_parser.add_argument("config", help="Path to YAML configuration")
    freeze_pubchem_parser.add_argument("--output", required=True, help="Output snapshot JSON path")
    freeze_pubchem_parser.add_argument("--live", action="store_true", help="Use live PubChem API in addition to any existing snapshot")
    freeze_pubchem_parser.add_argument("--existing", help="Optional existing snapshot to merge into")
    freeze_pubchem_parser.add_argument("--only-missing", action="store_true", help="Resolve only keys not already present in the existing snapshot")
    freeze_pubchem_parser.add_argument("--lock-output", help="Optional lock JSON path")

    materialize_state_parser = subparsers.add_parser("materialize-state-catalog", help="Materialize a design-time state master into a runtime species catalog YAML")
    materialize_state_parser.add_argument("state_master", help="Path to state_master_base YAML")
    materialize_state_parser.add_argument("--output", required=True, help="Output species catalog YAML path")
    materialize_state_parser.add_argument("--families", nargs="*", help="Optional chemistry-family filter")
    materialize_state_parser.add_argument("--charge-window-min", type=int)
    materialize_state_parser.add_argument("--charge-window-max", type=int)
    materialize_state_parser.add_argument("--include-disabled", action="store_true", help="Include disabled state master entries")
    materialize_state_parser.add_argument("--asd-export-paths", nargs="*", help="Optional ASD CSV exports for source-backed atomic excited-state expansion")
    materialize_state_parser.add_argument("--asd-max-ion-charge", type=int, default=0)
    materialize_state_parser.add_argument("--asd-max-levels-per-spectrum", type=int, default=0)

    qdb_parser = subparsers.add_parser("fetch-qdb-raw", help="Download raw QDB chemistry text using the public API")
    qdb_parser.add_argument("chemistry_id", type=int)
    qdb_parser.add_argument("--api-key-env", default="QDB_API_KEY")
    qdb_parser.add_argument("--output", required=True)

    visualize_parser = subparsers.add_parser("visualize", help="Render DAGs, summaries, and paginated list views from a built network")
    visualize_parser.add_argument("network", help="Path to built network JSON")
    visualize_parser.add_argument("--config", help="Optional config YAML path for dictionary views")
    visualize_parser.add_argument("--output-dir", required=True, help="Directory for PNG/CSV visualization artifacts")
    visualize_parser.add_argument("--views", nargs="*", default=["all"], help="View ids, audience tags, or all")
    visualize_parser.add_argument("--dpi", type=int, default=180)
    visualize_parser.add_argument("--max-reactions-in-graph", type=int, default=80)

    audit_config_parser = subparsers.add_parser("audit-config", help="Summarize resolved config inputs, fallback catalogs, and configured sources")
    audit_config_parser.add_argument("config", help="Path to YAML configuration")
    audit_config_parser.add_argument("--output", help="Optional JSON output path")
    audit_config_parser.add_argument("--head-vamdc", action="store_true", help="Run VAMDC HEAD preflight for live queries")

    audit_parser = subparsers.add_parser("audit-network", help="Summarize origin/fallback usage from a built network JSON")
    audit_parser.add_argument("network", help="Path to built network JSON")
    audit_parser.add_argument("--output", help="Optional JSON output path")
    return parser


def _write_json_payload(path: str | Path, payload: object) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def _emit_json_payload(
    payload: object,
    *,
    output_path: str | Path | None = None,
    success_message: str,
) -> int:
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(f"{success_message} {output}")
    else:
        print(text)
    return 0


def _inspect_runtime_sources(runtime: AppRuntime, *, head_vamdc: bool = False) -> dict[str, object]:
    return inspect_sources(
        runtime.config,
        head_vamdc=head_vamdc,
        alias_resolver=runtime.alias_resolver,
        strength_registry=runtime.strength_registry,
    )


def _build_manifest(runtime: AppRuntime) -> dict[str, object]:
    return build_evidence_manifest(runtime.indexes, config_path=runtime.config.config_path)


def _build_catalog_summary(runtime: AppRuntime) -> dict[str, object]:
    return build_catalog_manifest(
        runtime.catalog,
        config_path=runtime.config.config_path,
        reaction_conflict_policy=runtime.config.catalog_policy.reaction_conflict_policy,
    )


def _write_lock_file(
    runtime: AppRuntime,
    *,
    output_path: str | Path,
    evidence_manifest: dict[str, object] | None,
    catalog_manifest: dict[str, object] | None,
    head_vamdc: bool = False,
) -> Path:
    inspection = _inspect_runtime_sources(runtime, head_vamdc=head_vamdc)
    payload = build_source_lock(
        runtime.config,
        inspection_report=inspection,
        evidence_manifest=evidence_manifest,
        catalog_manifest=catalog_manifest,
    )
    return _write_json_payload(output_path, payload)


def _collect_evidence_records(runtime: AppRuntime) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for index in runtime.indexes:
        for entry in index.entries:
            records.append(
                {
                    "source_system": entry.source_system,
                    "source_name": entry.source_name,
                    "reactants": list(entry.reactants),
                    "products": list(entry.products),
                    "citation": entry.citation,
                    "source_url": entry.source_url,
                    "support_score": entry.support_score,
                    "note": entry.note,
                    "metadata": dict(entry.metadata),
                }
            )
    return records


def _handle_build(args: argparse.Namespace) -> int:
    runtime = build_runtime(args.config)
    builder = runtime.build_network_builder()
    result = builder.build()
    manifest = _build_manifest(runtime)
    catalog_manifest = _build_catalog_summary(runtime)
    inspection = _inspect_runtime_sources(runtime, head_vamdc=False)
    result.metadata.update(
        {
            "config_sha256": inspection["config_sha256"],
            "config_sources": list(runtime.config.config_sources),
            "alias_count": len(runtime.alias_resolver.alias_map),
            "source_manifest": manifest,
            "catalog_manifest": catalog_manifest,
            "catalog_policy": runtime.config.catalog_policy.as_dict(),
            "source_profiles_path": runtime.config.source_profiles_path,
        }
    )
    result.write_json(args.output)
    if args.lock_output:
        _write_lock_file(
            runtime,
            output_path=args.lock_output,
            evidence_manifest=manifest,
            catalog_manifest=catalog_manifest,
            head_vamdc=bool(args.head_vamdc),
        )
    print(f"Wrote {len(result.species)} species and {len(result.reactions)} reactions to {args.output}")
    return 0


def _handle_validate_config(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    print(config.to_json())
    return 0


def _handle_collect_evidence(args: argparse.Namespace) -> int:
    runtime = build_runtime(args.config)
    payload = {
        "manifest": _build_manifest(runtime),
        "records": _collect_evidence_records(runtime),
    }
    if args.merge and args.existing:
        payload = merge_evidence_payloads(load_json_if_exists(args.existing), payload)
    output = _write_json_payload(args.output, payload)
    if args.lock_output:
        _write_lock_file(
            runtime,
            output_path=args.lock_output,
            evidence_manifest=payload.get("manifest"),
            catalog_manifest=_build_catalog_summary(runtime),
            head_vamdc=bool(args.head_vamdc),
        )
    print(f"Wrote {len(payload['records'])} normalized evidence records to {output}")
    return 0


def _handle_inspect_sources(args: argparse.Namespace) -> int:
    runtime = build_runtime(args.config, include_evidence_indexes=False)
    report = _inspect_runtime_sources(runtime, head_vamdc=bool(args.head_vamdc))
    return _emit_json_payload(
        report,
        output_path=args.output,
        success_message="Wrote source inspection report to",
    )


def _handle_write_lock(args: argparse.Namespace) -> int:
    runtime = build_runtime(args.config)
    manifest = _build_manifest(runtime)
    output = _write_lock_file(
        runtime,
        output_path=args.output,
        evidence_manifest=manifest,
        catalog_manifest=_build_catalog_summary(runtime),
        head_vamdc=bool(args.head_vamdc),
    )
    print(f"Wrote source lock to {output}")
    return 0


def _handle_freeze_pubchem(args: argparse.Namespace) -> int:
    runtime = build_runtime(args.config)
    existing_path = args.existing or (args.output if Path(args.output).exists() else None)
    payload = build_pubchem_snapshot(
        runtime.config,
        live_api=bool(args.live),
        existing_path=existing_path,
        only_missing=bool(args.only_missing),
    )
    output = _write_json_payload(args.output, payload)
    if args.lock_output:
        _write_lock_file(
            runtime,
            output_path=args.lock_output,
            evidence_manifest=_build_manifest(runtime),
            catalog_manifest=_build_catalog_summary(runtime),
        )
    print(f"Wrote {len(payload)} PubChem identity records to {output}")
    return 0


def _handle_materialize_state_catalog(args: argparse.Namespace) -> int:
    asd = None
    if args.asd_export_paths:
        asd = NistAsdBootstrapAdapter(args.asd_export_paths)
    output = materialize_state_master_file(
        args.state_master,
        output_path=args.output,
        families=args.families,
        charge_window_min=args.charge_window_min,
        charge_window_max=args.charge_window_max,
        include_disabled=bool(args.include_disabled),
        asd=asd,
        asd_max_ion_charge=int(args.asd_max_ion_charge),
        asd_max_levels_per_spectrum=int(args.asd_max_levels_per_spectrum),
    )
    print(f"Wrote materialized species catalog to {output}")
    return 0


def _handle_visualize(args: argparse.Namespace) -> int:
    artifacts = render_visualizations(
        network_path=args.network,
        config_path=args.config,
        output_dir=args.output_dir,
        views=args.views,
        dpi=int(args.dpi),
        max_reactions_in_graph=int(args.max_reactions_in_graph),
    )
    print(f"Wrote {len(artifacts)} visualization artifacts to {args.output_dir}")
    return 0


def _handle_audit_config(args: argparse.Namespace) -> int:
    runtime = build_runtime(args.config)
    audit = build_runtime_audit(runtime, head_vamdc=bool(args.head_vamdc))
    return _emit_json_payload(
        audit,
        output_path=args.output,
        success_message="Wrote config audit report to",
    )


def _handle_audit_network(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.network).read_text(encoding="utf-8"))
    audit = build_network_manifest_from_payload(payload)
    return _emit_json_payload(
        audit,
        output_path=args.output,
        success_message="Wrote network audit report to",
    )


def _handle_fetch_qdb_raw(args: argparse.Namespace) -> int:
    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise SystemExit(f"Environment variable {args.api_key_env} is not set.")
    client = QdbApiClient(api_key=api_key)
    raw = client.fetch_chemistry_raw(args.chemistry_id)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(raw, encoding="utf-8")
    print(f"Wrote raw QDB response to {output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "build": _handle_build,
        "validate-config": _handle_validate_config,
        "collect-evidence": _handle_collect_evidence,
        "inspect-sources": _handle_inspect_sources,
        "write-lock": _handle_write_lock,
        "freeze-pubchem": _handle_freeze_pubchem,
        "materialize-state-catalog": _handle_materialize_state_catalog,
        "visualize": _handle_visualize,
        "audit-config": _handle_audit_config,
        "audit-network": _handle_audit_network,
        "fetch-qdb-raw": _handle_fetch_qdb_raw,
    }
    handler = handlers.get(args.command)
    if handler is None:
        raise SystemExit(2)
    return handler(args)
