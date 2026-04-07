from plasma_reaction_builder.config import load_config
from plasma_reaction_builder.source_ops import build_catalog_manifest, build_evidence_manifest, build_pubchem_snapshot, inspect_sources
from plasma_reaction_builder.adapters import ReactionEvidenceFactory
from plasma_reaction_builder.catalog import TemplateCatalog
from plasma_reaction_builder.model import ReactionTemplate


def test_inspect_sources_reports_local_counts():
    config = load_config("examples/config.yaml")
    report = inspect_sources(config)
    assert report["pubchem"]["enabled"] is True
    assert report["nist_asd"]["bootstrap_species_count"] > 0
    kinds = {item["kind"]: item for item in report["reaction_evidence"]}
    assert kinds["umist_ratefile"]["record_count"] > 0
    assert kinds["kida_network"]["record_count"] > 0
    assert kinds["vamdc_xsams"]["record_count"] > 0


def test_build_pubchem_snapshot_from_existing_snapshot():
    config = load_config("examples/config.yaml")
    payload = build_pubchem_snapshot(config, live_api=False)
    assert "name:methane" in payload
    assert payload["name:methane"]["formula"] == "CH4"


def test_manifest_counts_indexes():
    config = load_config("examples/config.yaml")
    factory = ReactionEvidenceFactory()
    indexes = factory.build_indexes(
        config.bootstrap.reaction_evidence.sources,
        feed_formulas=[feed.formula for feed in config.feeds],
    )
    manifest = build_evidence_manifest(indexes, config_path=config.config_path)
    assert manifest["total_records"] >= 1
    assert any(item["source_id"] == "umist" for item in manifest["sources"])


def test_catalog_manifest_reports_template_origins_and_conflicts():
    catalog = TemplateCatalog(species_library={}, templates=[], loaded_resources=["catalog_00_references.yaml"])
    curated = ReactionTemplate(
        key="curated::1",
        reactants=["CH4"],
        products=["CH3", "H"],
        lhs_tokens=["e-", "CH4"],
        rhs_tokens=["e-", "CH3", "H"],
        family="electron_dissociation",
        metadata={"template_origin": "curated_catalog", "template_priority": 20},
    )
    promoted = ReactionTemplate(
        key="promo::1",
        reactants=["CH4"],
        products=["CH3", "H"],
        lhs_tokens=["e-", "CH4"],
        rhs_tokens=["e-", "CH3", "H"],
        family="electron_dissociation",
        metadata={
            "template_origin": "source_backed_promotion",
            "template_priority": 60,
            "template_source_system": "qdb",
        },
    )
    catalog.merge_templates([curated], merge_reason="initial")
    catalog.merge_templates([promoted], equation_conflict_policy="prefer_higher_priority", merge_reason="promotion")

    manifest = build_catalog_manifest(
        catalog,
        config_path="examples/config.yaml",
        reaction_conflict_policy="prefer_higher_priority",
    )

    assert manifest["reaction_conflict_policy"] == "prefer_higher_priority"
    assert any(item["name"] == "source_backed_promotion" for item in manifest["templates_by_origin"])
    assert any(item["name"] == "qdb" for item in manifest["template_source_systems"])
    assert manifest["template_source_names"] == []
    assert any(item["action"] == "replaced_equation_match" for item in manifest["equation_conflicts"])


def test_inspect_sources_treats_disabled_bootstrap_steps_as_ready_when_not_required():
    config = load_config("examples/production_blueprint/config_bromine_family_runtime.yaml")

    report = inspect_sources(config)

    assert report["summary"]["reaction_evidence_required"] is True
    assert report["summary"]["bootstrap_ready"] is True
    assert report["summary"]["build_ready"] is True
