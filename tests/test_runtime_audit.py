from pathlib import Path

from plasma_reaction_builder.runtime import build_runtime
from plasma_reaction_builder.runtime_audit import build_runtime_audit


def test_runtime_audit_reports_fallback_catalogs_and_promoted_sources():
    runtime = build_runtime("examples/production_blueprint/config_bromine_family_runtime.yaml")

    audit = build_runtime_audit(runtime)

    assert audit["summary"]["build_ready"] is True
    assert audit["summary"]["fallback_catalog_count"] >= 1
    assert audit["promotion_summary"]["source_backed_templates"]["enabled"] is True
    assert audit["promotion_summary"]["source_backed_templates"]["promoted_template_count"] >= 1
    assert audit["promotion_summary"]["source_backed_templates"]["template_source_systems"] == [{"name": "qdb", "count": 2}]
    assert audit["promotion_summary"]["molecular_excited_states"]["configured_sources"] == []
    assert audit["promotion_summary"]["molecular_excited_state_templates"]["configured_sources"] == []
    assert any(Path(item["path"]).name == "catalog_00_references.yaml" for item in audit["reference_catalogs"])
    assert any(Path(item["path"]).name == "catalog_49_reactions_electron_attachment_bromine.yaml" for item in audit["fallback_catalogs"])
    assert any(item["source_system"] == "qdb" for item in audit["source_readiness"])
    assert audit["source_manifest"]["total_records"] >= 1
