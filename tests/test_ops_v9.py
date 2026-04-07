from plasma_reaction_builder.normalization import AliasResolver
from plasma_reaction_builder.catalog import TemplateCatalog
from plasma_reaction_builder.config import load_config
from plasma_reaction_builder.source_ops import build_source_lock, inspect_sources, merge_evidence_payloads
from plasma_reaction_builder.runtime import build_runtime
from plasma_reaction_builder.formula import parse_species_token, parse_formula
from plasma_reaction_builder.model import ReactionTemplate


def test_isomer_prefixed_token_exposes_formula():
    parsed = parse_species_token("c-C4F8+")
    assert parsed.formula == "C4F8"
    assert parse_formula(parsed.formula) == {"C": 4, "F": 8}


def test_alias_resolver_preserves_charge_when_relabeling():
    resolver = AliasResolver(alias_map={"C4F8": "c-C4F8"})
    assert resolver.canonicalize_token("C4F8+") == "c-C4F8+"
    assert resolver.canonicalize_token("C4F8-") == "c-C4F8-"


def test_source_profiles_are_attached_to_external_evidence():
    runtime = build_runtime("examples/config.yaml")
    assert any(index.entries[0].metadata.get("source_family") for index in runtime.indexes if index.entries)


def test_lock_contains_config_hash_and_summary():
    runtime = build_runtime("examples/config.yaml", include_evidence_indexes=False)
    inspection = inspect_sources(runtime.config, alias_resolver=runtime.alias_resolver, strength_registry=runtime.strength_registry)
    lock = build_source_lock(runtime.config, inspection_report=inspection, evidence_manifest={"total_records": 1})
    assert len(lock["config_sha256"]) == 64
    assert "config_sources" in lock
    assert "catalog_policy" in lock
    assert "summary" in lock["inspection"]
    assert "state_masters" in lock
    assert "state_filters" in lock
    assert "state_promotions" in lock
    assert "template_promotions" in lock
    assert "excited_state_registry_path" in lock


def test_merge_evidence_payloads_dedupes_by_reaction_identity():
    existing = {
        "manifest": {"total_records": 1},
        "records": [
            {
                "source_system": "umist",
                "source_name": "UMIST",
                "reactants": ["CH3", "H"],
                "products": ["CH4"],
                "citation": "r1",
                "source_url": None,
            }
        ],
    }
    new = {
        "manifest": {"total_records": 2},
        "records": [
            {
                "source_system": "umist",
                "source_name": "UMIST",
                "reactants": ["CH3", "H"],
                "products": ["CH4"],
                "citation": "r1",
                "source_url": None,
                "note": "newer",
            },
            {
                "source_system": "kida",
                "source_name": "KIDA",
                "reactants": ["CH3", "H"],
                "products": ["CH4"],
                "citation": "r2",
                "source_url": None,
            },
        ],
    }
    merged = merge_evidence_payloads(existing, new)
    assert merged["merge_summary"]["final_record_count"] == 2
    assert merged["manifest"]["total_records"] == 2


def test_load_config_parses_state_filters(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "feeds:",
                "  - species_key: CH4",
                "    formula: CH4",
                "state_filters:",
                "  charge_window_min: -1",
                "  charge_window_max: 1",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.state_filters.charge_window_min == -1
    assert config.state_filters.charge_window_max == 1


def test_load_config_parses_state_masters(tmp_path):
    state_master_path = tmp_path / "state_master.yaml"
    state_master_path.write_text(
        "\n".join(
            [
                "state_master:",
                "  - family: noble_gas",
                "    species_id: argon",
                "    preferred_key: Ar",
                "    display_name: Argon",
                "    formula: Ar",
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "feeds:",
                "  - species_key: Ar",
                "    formula: Ar",
                "state_masters:",
                "  - path: state_master.yaml",
                "    families: [noble_gas]",
                "    include_disabled: false",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert len(config.state_masters) == 1
    assert config.state_masters[0].families == ["noble_gas"]
    assert config.state_masters[0].include_disabled is False
    assert config.state_masters[0].path == str(state_master_path.resolve())


def test_load_config_parses_state_promotions(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "feeds:",
                "  - species_key: CH4",
                "    formula: CH4",
                "state_promotions:",
                "  molecular_excited_states:",
                "    enabled: true",
                "    source_systems: [qdb, ideadb]",
                "    min_support_score: 0.8",
                "    max_states_per_species: 2",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.state_promotions.molecular_excited_states.enabled is True
    assert config.state_promotions.molecular_excited_states.source_systems == ["qdb", "ideadb"]
    assert config.state_promotions.molecular_excited_states.max_states_per_species == 2


def test_load_config_parses_template_promotions(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "feeds:",
                "  - species_key: Br2",
                "    formula: Br2",
                "template_promotions:",
                "  source_backed_templates:",
                "    enabled: true",
                "    source_systems: [qdb, nist_kinetics]",
                "    target_families: [bromine]",
                "    allowed_reaction_families: [ion_neutral_followup, radical_neutral_reaction]",
                "    min_support_score: 0.82",
                "    max_templates_per_family: 3",
                "    require_catalog_species: true",
                "  molecular_excited_state_templates:",
                "    enabled: true",
                "    source_systems: [qdb, vamdc]",
                "    target_families: [oxygen, nitrogen]",
                "    min_support_score: 0.8",
                "    include_electron_excitation: true",
                "    include_radiative_relaxation: true",
                "    include_collisional_quenching: true",
                "    include_superelastic_deexcitation: true",
                "    quenching_partners:",
                "      oxygen: [O2, N2]",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.template_promotions.source_backed_templates.enabled is True
    assert config.template_promotions.source_backed_templates.source_systems == ["qdb", "nist_kinetics"]
    assert config.template_promotions.source_backed_templates.target_families == ["bromine"]
    assert config.template_promotions.source_backed_templates.allowed_reaction_families == [
        "ion_neutral_followup",
        "radical_neutral_reaction",
    ]
    assert config.template_promotions.source_backed_templates.max_templates_per_family == 3
    assert config.template_promotions.molecular_excited_state_templates.enabled is True
    assert config.template_promotions.molecular_excited_state_templates.source_systems == ["qdb", "vamdc"]
    assert config.template_promotions.molecular_excited_state_templates.target_families == ["oxygen", "nitrogen"]
    assert config.template_promotions.molecular_excited_state_templates.include_radiative_relaxation is True
    assert config.template_promotions.molecular_excited_state_templates.include_collisional_quenching is True
    assert config.template_promotions.molecular_excited_state_templates.include_superelastic_deexcitation is True
    assert config.template_promotions.molecular_excited_state_templates.quenching_partners == {
        "oxygen": ["O2", "N2"],
    }


def test_load_config_parses_excited_state_registry_path(tmp_path):
    registry_path = tmp_path / "excited_state_registry.yaml"
    registry_path.write_text(
        "\n".join(
            [
                "excited_state_registry:",
                "  - canonical_key: O2[a1Delta_g]",
                "    label_synonyms: [a1Delta_g]",
            ]
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "feeds:",
                "  - species_key: O2",
                "    formula: O2",
                "excited_state_registry_path: excited_state_registry.yaml",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.excited_state_registry_path == str(registry_path.resolve())


def test_load_config_supports_extends_and_preserves_source_order(tmp_path):
    base_catalog = tmp_path / "catalog.yaml"
    base_catalog.write_text("references: {}\n", encoding="utf-8")
    base_state_master = tmp_path / "state_master.yaml"
    base_state_master.write_text("state_master: []\n", encoding="utf-8")
    base_config = tmp_path / "base.yaml"
    base_config.write_text(
        "\n".join(
            [
                "catalog_paths:",
                "  - catalog.yaml",
                "catalog_policy:",
                "  reaction_conflict_policy: prefer_higher_priority",
                "state_masters:",
                "  - path: state_master.yaml",
                "    families: [oxygen]",
            ]
        ),
        encoding="utf-8",
    )
    child_config = tmp_path / "child.yaml"
    child_config.write_text(
        "\n".join(
            [
                "extends: base.yaml",
                "feeds:",
                "  - species_key: O2",
                "    formula: O2",
                "catalog_paths:",
                "  - catalog.yaml",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(child_config)

    assert config.catalog_policy.reaction_conflict_policy == "prefer_higher_priority"
    assert config.catalog_paths == [str(base_catalog.resolve())]
    assert config.state_masters[0].path == str(base_state_master.resolve())
    assert config.config_sources == [str(base_config.resolve()), str(child_config.resolve())]


def test_catalog_prefer_higher_priority_replaces_equation_match():
    catalog = TemplateCatalog(species_library={}, templates=[], loaded_resources=[])
    curated = ReactionTemplate(
        key="curated::same_eq",
        reactants=["O2"],
        products=["O", "O"],
        lhs_tokens=["e-", "O2"],
        rhs_tokens=["e-", "O", "O"],
        family="electron_dissociation",
        metadata={"template_origin": "curated_catalog", "template_priority": 20},
    )
    promoted = ReactionTemplate(
        key="promo::same_eq",
        reactants=["O2"],
        products=["O", "O"],
        lhs_tokens=["e-", "O2"],
        rhs_tokens=["e-", "O", "O"],
        family="electron_dissociation",
        metadata={"template_origin": "source_backed_promotion", "template_priority": 60},
    )

    first = catalog.merge_templates([curated], equation_conflict_policy="keep_existing", merge_reason="initial")
    second = catalog.merge_templates([promoted], equation_conflict_policy="prefer_higher_priority", merge_reason="promotion")

    assert first.added == 1
    assert second.replaced == 1
    assert [template.key for template in catalog.templates] == ["promo::same_eq"]
    assert any(event["action"] == "replaced_equation_match" for event in catalog.template_merge_events)
