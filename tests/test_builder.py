from pathlib import Path

from plasma_reaction_builder.builder import NetworkBuilder
from plasma_reaction_builder.catalog import TemplateCatalog
from plasma_reaction_builder.config import AtctOptions, BootstrapOptions, BuildConfig, FeedSpec, StateFilterOptions, StateMasterSourceSpec
from plasma_reaction_builder.model import ReactionRecord, ReactionTemplate
from plasma_reaction_builder.provenance import EvidenceRecord
from plasma_reaction_builder.runtime import build_runtime


def _build_species_keys_and_families(config_path: str):
    runtime = build_runtime(config_path, include_evidence_indexes=False)
    result = runtime.build_network_builder().build()
    species_keys = {species.prototype_key for species in result.species}
    reaction_families = {reaction.family for reaction in result.reactions}
    return runtime, species_keys, reaction_families


def test_full_build_runs():
    runtime = build_runtime("examples/config.yaml")
    builder = runtime.build_network_builder()
    result = builder.build()
    assert result.metadata["species_count"] > 10
    assert result.metadata["reaction_count"] > 5
    ch4 = next(species for species in result.species if species.prototype_key == "CH4")
    assert ch4.identity is not None
    assert any(state.prototype_key.startswith("C[") for state in result.species)
    assert any(any(record.source_system in {"qdb", "umist", "kida", "ideadb", "nist_kinetics"} for record in reaction.evidence) for reaction in result.reactions)


def test_external_evidence_prevents_endothermic_pruning():
    template = ReactionTemplate(
        key="ext::umist::keep",
        reactants=["CH3", "H"],
        products=["CH4"],
        lhs_tokens=["CH3", "H"],
        rhs_tokens=["CH4"],
        family="gas_phase_evidence",
        delta_h_kj_mol=450.0,
    )
    catalog = TemplateCatalog(
        species_library={},
        templates=[template],
        loaded_resources=[],
    )
    config = BuildConfig(
        feeds=[FeedSpec(species_key="CH4", formula="CH4")],
        bootstrap=BootstrapOptions(
            atct=AtctOptions(hard_endothermic_kj_mol=320.0),
        ),
    )
    builder = NetworkBuilder(config=config, catalog=catalog)
    reaction = ReactionRecord(
        key=template.key,
        family=template.family,
        equation=template.equation(),
        reactant_state_ids=[],
        product_state_ids=[],
        reactant_keys=list(template.reactants),
        product_keys=list(template.products),
        lhs_tokens=list(template.lhs_tokens),
        rhs_tokens=list(template.rhs_tokens),
        generation=1,
        delta_h_kj_mol=template.delta_h_kj_mol,
        evidence=[
            EvidenceRecord(
                source_system="umist",
                source_name="UMIST",
                acquisition_method="offline_snapshot",
                evidence_kind="direct_database_record",
                support_score=0.52,
            )
        ],
    )
    builder.reactions_by_key[reaction.dedupe_key()] = reaction

    builder._annotate_reactions()

    assert reaction.dedupe_key() in builder.reactions_by_key


def test_template_only_evidence_is_still_prunable():
    template = ReactionTemplate(
        key="pkg::template::prune",
        reactants=["CH3", "H"],
        products=["CH4"],
        lhs_tokens=["CH3", "H"],
        rhs_tokens=["CH4"],
        family="gas_phase_evidence",
        delta_h_kj_mol=450.0,
    )
    catalog = TemplateCatalog(
        species_library={},
        templates=[template],
        loaded_resources=[],
    )
    config = BuildConfig(
        feeds=[FeedSpec(species_key="CH4", formula="CH4")],
        bootstrap=BootstrapOptions(
            atct=AtctOptions(hard_endothermic_kj_mol=320.0),
        ),
    )
    builder = NetworkBuilder(config=config, catalog=catalog)
    reaction = ReactionRecord(
        key=template.key,
        family=template.family,
        equation=template.equation(),
        reactant_state_ids=[],
        product_state_ids=[],
        reactant_keys=list(template.reactants),
        product_keys=list(template.products),
        lhs_tokens=list(template.lhs_tokens),
        rhs_tokens=list(template.rhs_tokens),
        generation=1,
        delta_h_kj_mol=template.delta_h_kj_mol,
        evidence=[
            EvidenceRecord(
                source_system="template_library",
                source_name="Packaged templates",
                acquisition_method="package_template",
                evidence_kind="curated_reaction_family",
                support_score=0.78,
            )
        ],
    )
    builder.reactions_by_key[reaction.dedupe_key()] = reaction

    builder._annotate_reactions()

    assert reaction.dedupe_key() not in builder.reactions_by_key


def test_build_respects_charge_window_for_catalog_and_templates():
    config = BuildConfig(
        feeds=[FeedSpec(species_key="CH4", formula="CH4")],
        projectiles=["e-"],
        libraries=["ch4"],
        state_filters=StateFilterOptions(charge_window_min=0, charge_window_max=0),
    )
    catalog = TemplateCatalog.from_sources(
        config.libraries,
        config.catalog_paths,
        charge_window_min=config.state_filters.charge_window_min,
        charge_window_max=config.state_filters.charge_window_max,
    )
    builder = NetworkBuilder(config=config, catalog=catalog)

    result = builder.build()

    assert result.reactions
    assert all(species.charge == 0 for species in result.species)
    assert all("+" not in key and "-" not in key for reaction in result.reactions for key in reaction.product_keys)


def test_build_runtime_materializes_state_masters_for_feed_species(tmp_path: Path):
    state_master = tmp_path / "state_master.yaml"
    state_master.write_text(
        "\n".join(
            [
                "state_master:",
                "  - family: noble_gas",
                "    species_id: xenon_atom",
                "    preferred_key: Xe",
                "    display_name: Xenon",
                "    formula: Xe",
                "    aliases: [xenon]",
                "    tags: [core, noble_gas]",
                "    allowed_charges: [0, 1]",
                "    enabled: true",
                "  - family: hydrocarbon",
                "    species_id: test_hydrocarbon",
                "    preferred_key: C13H28",
                "    display_name: Tridecane",
                "    formula: C13H28",
                "    allowed_charges: [0, 1]",
                "    enabled: true",
            ]
        ),
        encoding="utf-8",
    )
    config = BuildConfig(
        feeds=[FeedSpec(species_key="Xe", formula="Xe")],
        libraries=[],
        state_masters=[StateMasterSourceSpec(path=str(state_master), families=["noble_gas"])],
        state_filters=StateFilterOptions(charge_window_min=0, charge_window_max=0),
    )

    runtime = build_runtime(config, include_evidence_indexes=False)
    result = runtime.build_network_builder().build()

    assert "Xe" in runtime.catalog.species_library
    assert "Xe+" not in runtime.catalog.species_library
    assert "C13H28" not in runtime.catalog.species_library
    assert any(item.startswith(f"state_master:{state_master}") for item in runtime.catalog.loaded_resources)
    assert any(species.prototype_key == "Xe" for species in result.species)
    assert not any(diag.code == "generic_state" and diag.context.get("species_key") == "Xe" for diag in result.diagnostics)


def test_production_blueprint_build_uses_excitation_and_charge_transfer_families():
    runtime = build_runtime("examples/production_blueprint/config_state_master_runtime.yaml", include_evidence_indexes=False)
    result = runtime.build_network_builder().build()

    species_keys = {species.prototype_key for species in result.species}
    reaction_families = {reaction.family for reaction in result.reactions}
    template_families = {template.family for template in runtime.catalog.templates}
    catalog_keys = set(runtime.catalog.species_library)

    assert "Ar[1s5]" in species_keys
    assert "CH4[V13]" in species_keys
    assert "O2[a1Delta_g]" in species_keys
    assert "N2[A3Sigma_u_plus]" in species_keys
    assert "O[1D_2]" in catalog_keys
    assert "N[2D_5/2]" in catalog_keys
    assert "electron_excitation" in reaction_families
    assert "electron_excitation_vibrational" in reaction_families
    assert "charge_transfer" in reaction_families
    assert "electron_attachment" in reaction_families
    assert "electron_dissociation" in reaction_families
    assert "ion_neutral_followup" in template_families
    assert "neutral_fragmentation" in template_families
    assert "radical_fragmentation" in template_families


def test_gas_phase_target_runtime_includes_requested_feedstocks_and_parent_ionization():
    runtime = build_runtime(
        "examples/production_blueprint/config_gas_phase_target_runtime.yaml",
        include_evidence_indexes=False,
    )
    result = runtime.build_network_builder().build()

    catalog_keys = set(runtime.catalog.species_library)
    species_keys = {species.prototype_key for species in result.species}
    reaction_families = {reaction.family for reaction in result.reactions}
    template_keys = {template.key for template in runtime.catalog.templates}

    assert "He" in catalog_keys
    assert "H2" in catalog_keys
    assert "CF4" in catalog_keys
    assert "CHF3" in catalog_keys
    assert "CH2F2" in catalog_keys
    assert "CH3F" in catalog_keys
    assert "C2F6" in catalog_keys
    assert "c-C4F8" in catalog_keys
    assert "C5F8" in catalog_keys
    assert "SF6" in catalog_keys
    assert "NF3" in catalog_keys
    assert "Cl2" in catalog_keys
    assert "HBr" in catalog_keys
    assert "HCl" in catalog_keys
    assert "BCl3" in catalog_keys
    assert "SiH4" in catalog_keys
    assert "NH3" in catalog_keys
    assert "N2O" in catalog_keys
    assert "O3" in catalog_keys
    assert "SiH2Cl2" in catalog_keys
    assert "SiHCl3" in catalog_keys
    assert "WF6" in catalog_keys
    assert "SF5" in catalog_keys
    assert "SF4" in catalog_keys
    assert "NF2" in catalog_keys
    assert "NH2" in catalog_keys
    assert "NO" in catalog_keys
    assert "BCl2" in catalog_keys
    assert "WF5" in catalog_keys
    assert "WF4" in catalog_keys
    assert "C6H15O3Si" in catalog_keys
    assert "C2H5O" in catalog_keys
    assert "C8H20O4Si" in catalog_keys

    assert "He+" in species_keys
    assert "H2+" in species_keys
    assert "CF4+" in species_keys
    assert "Cl2-" in species_keys
    assert "SF6-" in species_keys
    assert "SiH4+" in species_keys
    assert "WF6+" in species_keys
    assert "SF5" in species_keys
    assert "NF2" in species_keys
    assert "NH2" in species_keys
    assert "NO" in species_keys
    assert "BCl2" in species_keys
    assert "WF5" in species_keys
    assert "C6H15O3Si" in species_keys
    assert "C2H5O" in species_keys
    assert "C8H20O4Si+" in species_keys

    assert "electron_ionization" in reaction_families
    assert "electron_attachment" in reaction_families
    assert "electron_dissociation" in reaction_families

    assert "process_gases::electron_dissociation::sf6_to_sf5_f" in template_keys
    assert "process_gases::dissociative_recombination::nh3_plus" in template_keys
    assert "advanced_precursors::electron_dissociation::teos_to_triethoxysilyl_ethoxy" in template_keys
    assert "advanced_precursors::ion_neutral_followup::wf6_plus_h2" in template_keys


def test_chlorine_family_runtime_builds_minimal_family_pack():
    runtime, species_keys, reaction_families = _build_species_keys_and_families(
        "examples/production_blueprint/config_chlorine_family_runtime.yaml"
    )
    catalog_keys = set(runtime.catalog.species_library)

    assert "Cl" in catalog_keys
    assert "Cl2" in catalog_keys
    assert "Cl2-" in catalog_keys
    assert "Cl2+" in catalog_keys
    assert "HCl" in catalog_keys
    assert "HCl-" in catalog_keys
    assert "HCl+" in catalog_keys
    assert "H2" in catalog_keys

    assert "Cl2-" in species_keys
    assert "Cl2+" in species_keys
    assert "HCl+" in species_keys
    assert "Cl" in species_keys
    assert "Cl+" in species_keys
    assert "H" in species_keys

    assert "electron_attachment" in reaction_families
    assert "electron_ionization" in reaction_families
    assert "electron_dissociation" in reaction_families
    assert "radical_neutral_reaction" in reaction_families
    assert "ion_neutral_followup" in reaction_families
    assert "dissociative_recombination" in reaction_families


def test_bromine_family_runtime_builds_minimal_family_pack():
    runtime = build_runtime(
        "examples/production_blueprint/config_bromine_family_runtime.yaml",
        include_evidence_indexes=False,
    )
    result = runtime.build_network_builder().build()

    catalog_keys = set(runtime.catalog.species_library)
    species_keys = {species.prototype_key for species in result.species}
    reaction_families = {reaction.family for reaction in result.reactions}

    assert "Br" in catalog_keys
    assert "Br2" in catalog_keys
    assert "Br2-" in catalog_keys
    assert "Br2+" in catalog_keys
    assert "HBr" in catalog_keys
    assert "HBr-" in catalog_keys
    assert "HBr+" in catalog_keys
    assert "H2" in catalog_keys

    assert "Br2-" in species_keys
    assert "Br2+" in species_keys
    assert "HBr+" in species_keys
    assert "Br" in species_keys
    assert "H" in species_keys
    assert "Br+" in species_keys

    assert "template_promotion:source_backed_templates" in runtime.catalog.loaded_resources
    assert "electron_attachment" in reaction_families
    assert "electron_ionization" in reaction_families
    assert "electron_dissociation" in reaction_families
    assert "radical_neutral_reaction" in reaction_families
    assert "ion_neutral_followup" in reaction_families
    assert "dissociative_recombination" in reaction_families


def test_silicon_family_runtime_builds_minimal_family_pack():
    runtime = build_runtime(
        "examples/production_blueprint/config_silicon_family_runtime.yaml",
        include_evidence_indexes=False,
    )
    result = runtime.build_network_builder().build()

    catalog_keys = set(runtime.catalog.species_library)
    species_keys = {species.prototype_key for species in result.species}
    reaction_families = {reaction.family for reaction in result.reactions}

    assert "Si" in catalog_keys
    assert "SiH4" in catalog_keys
    assert "SiH4+" in catalog_keys
    assert "SiH3" in catalog_keys
    assert "SiH2" in catalog_keys
    assert "SiH" in catalog_keys
    assert "SiH2Cl2" in catalog_keys
    assert "SiH2Cl2+" in catalog_keys
    assert "SiHCl2" in catalog_keys
    assert "SiHCl3" in catalog_keys
    assert "SiHCl3+" in catalog_keys
    assert "SiCl3" in catalog_keys
    assert "SiCl2" in catalog_keys

    assert "SiH4+" in species_keys
    assert "SiH2Cl2+" in species_keys
    assert "SiHCl3+" in species_keys
    assert "SiH3" in species_keys
    assert "SiHCl2" in species_keys
    assert "SiCl3" in species_keys
    assert "H2+" in species_keys
    assert "HCl" in species_keys

    assert "template_promotion:source_backed_templates" in runtime.catalog.loaded_resources
    assert "electron_ionization" in reaction_families
    assert "electron_dissociation" in reaction_families
    assert "radical_neutral_reaction" in reaction_families
    assert "ion_neutral_followup" in reaction_families
    assert "dissociative_recombination" in reaction_families


def test_o2_electron_argon_ion_runtime_builds_expected_state_and_reaction_list():
    runtime = build_runtime(
        "examples/production_blueprint/config_o2_electron_argon_ion_runtime.yaml",
        include_evidence_indexes=False,
    )
    result = runtime.build_network_builder().build()

    species_keys = {species.prototype_key for species in result.species}
    reaction_equations = {reaction.equation for reaction in result.reactions}
    reaction_families = {reaction.family for reaction in result.reactions}

    assert "O2" in species_keys
    assert "Ar+" in species_keys
    assert "Ar" in species_keys
    assert "O2-" in species_keys
    assert "O2+" in species_keys
    assert "O" in species_keys
    assert "O+" in species_keys
    assert "O-" in species_keys
    assert "O2[a1Delta_g]" in species_keys
    assert "O2[b1Sigma_g_plus]" in species_keys

    assert "e- + O2 -> O2-" in reaction_equations
    assert "e- + O2 -> O- + O" in reaction_equations
    assert "e- + O2 -> e- + e- + O2+" in reaction_equations
    assert "e- + O2 -> e- + O + O" in reaction_equations
    assert "e- + O2 -> e- + O2(a1Delta_g)" in reaction_equations
    assert "e- + O2 -> e- + O2(b1Sigma_g+)" in reaction_equations
    assert "Ar+ + O2 -> Ar + O2+" in reaction_equations
    assert "e- + O2+ -> O + O" in reaction_equations
    assert "e- + O -> O-" in reaction_equations
    assert "Ar+ + O -> Ar + O+" in reaction_equations
    assert "Ar+ + O- -> Ar + O" in reaction_equations
    assert "Ar+ + O2- -> Ar + O2" in reaction_equations
    assert "O+ + O2 -> O + O2+" in reaction_equations

    assert "electron_attachment" in reaction_families
    assert "electron_ionization" in reaction_families
    assert "electron_dissociation" in reaction_families
    assert "electron_excitation" in reaction_families
    assert "charge_transfer" in reaction_families
    assert "dissociative_recombination" in reaction_families
    assert "mutual_neutralization" in reaction_families
    assert "ion_neutral_followup" in reaction_families


def test_process_gas_secondary_runtime_builds_second_generation_channels():
    runtime = build_runtime(
        "examples/production_blueprint/config_process_gas_secondary_runtime.yaml",
        include_evidence_indexes=False,
    )
    result = runtime.build_network_builder().build()

    catalog_keys = set(runtime.catalog.species_library)
    species_keys = {species.prototype_key for species in result.species}
    reaction_families = {reaction.family for reaction in result.reactions}

    assert "SF6" in catalog_keys
    assert "NF3" in catalog_keys
    assert "BCl3" in catalog_keys
    assert "NH3" in catalog_keys
    assert "N2O" in catalog_keys
    assert "O3" in catalog_keys
    assert "SF5" in catalog_keys
    assert "NF2" in catalog_keys
    assert "BCl2" in catalog_keys
    assert "NH2" in catalog_keys
    assert "NO" in catalog_keys

    assert "SF6+" in species_keys
    assert "NF3+" in species_keys
    assert "BCl3+" in species_keys
    assert "NH3+" in species_keys
    assert "N2O+" in species_keys
    assert "O3+" in species_keys
    assert "SF5" in species_keys
    assert "NF2" in species_keys
    assert "BCl2" in species_keys
    assert "NH2" in species_keys
    assert "NO" in species_keys
    assert "O2+" in species_keys
    assert "H2+" in species_keys

    assert "electron_ionization" in reaction_families
    assert "electron_attachment" in reaction_families
    assert "electron_dissociation" in reaction_families
    assert "ion_neutral_followup" in reaction_families
    assert "dissociative_recombination" in reaction_families


def test_advanced_precursor_runtime_builds_wf6_teos_and_silicon_halide_channels():
    runtime = build_runtime(
        "examples/production_blueprint/config_advanced_precursor_runtime.yaml",
        include_evidence_indexes=False,
    )
    result = runtime.build_network_builder().build()

    catalog_keys = set(runtime.catalog.species_library)
    species_keys = {species.prototype_key for species in result.species}
    reaction_families = {reaction.family for reaction in result.reactions}

    assert "WF6" in catalog_keys
    assert "WF5" in catalog_keys
    assert "WF4" in catalog_keys
    assert "C8H20O4Si" in catalog_keys
    assert "C6H15O3Si" in catalog_keys
    assert "C2H5O" in catalog_keys
    assert "SiH2Cl2" in catalog_keys
    assert "SiHCl3" in catalog_keys
    assert "SiCl2" in catalog_keys

    assert "WF6+" in species_keys
    assert "WF5" in species_keys
    assert "WF4" in species_keys
    assert "C8H20O4Si+" in species_keys
    assert "C6H15O3Si" in species_keys
    assert "C2H5O" in species_keys
    assert "SiH2Cl2+" in species_keys
    assert "SiHCl3+" in species_keys
    assert "SiCl2" in species_keys
    assert "H2+" in species_keys
    assert "O2+" in species_keys

    assert "electron_ionization" in reaction_families
    assert "electron_dissociation" in reaction_families
    assert "ion_neutral_followup" in reaction_families
    assert "dissociative_recombination" in reaction_families


def test_gas_phase_target_db_first_runtime_uses_minimal_curated_catalog_and_external_promotions():
    runtime = build_runtime(
        "examples/production_blueprint/config_gas_phase_target_db_first_runtime.yaml",
    )
    result = runtime.build_network_builder().build()

    catalog_resources = [
        item
        for item in runtime.catalog.loaded_resources
        if "catalog_" in item and item.endswith(".yaml")
    ]
    expected_reference_catalog = str(Path("examples/production_blueprint/catalog_00_references.yaml").resolve())

    assert catalog_resources == [expected_reference_catalog]
    assert runtime.config.catalog_policy.reaction_conflict_policy == "prefer_higher_priority"
    assert len(runtime.config.config_sources) >= 2
    assert "state_promotion:molecular_excited_states" in runtime.catalog.loaded_resources
    assert "template_promotion:source_backed_templates" in runtime.catalog.loaded_resources
    assert "template_promotion:molecular_excited_state_templates" in runtime.catalog.loaded_resources

    species_keys = {species.prototype_key for species in result.species}
    reaction_equations = {reaction.equation for reaction in result.reactions}
    reaction_families = {reaction.family for reaction in result.reactions}

    assert "Ar+" in species_keys
    assert "O+" in species_keys
    assert "CH4[V14]" in runtime.catalog.species_library
    assert "O2[c1Sigma_u_minus]" in runtime.catalog.species_library
    assert "WF6[B1]" in runtime.catalog.species_library

    assert "e- + Ar -> e- + e- + Ar+" in reaction_equations
    assert "Ar+ + O2 -> Ar + O2+" in reaction_equations
    assert "e- + O2+ -> O + O" in reaction_equations
    assert "Ar+ + O- -> Ar + O" in reaction_equations
    assert "e- + CF4 -> e- + CF3 + F" in reaction_equations
    assert "Br + HBr -> Br2 + H" in reaction_equations
    assert "e- + SF6 -> e- + SF4 + F + F" in reaction_equations
    assert "WF6[B1] + H2 -> WF5 + F + H2" in reaction_equations

    assert "charge_transfer" in reaction_families
    assert "mutual_neutralization" in reaction_families
    assert "electron_dissociation" in reaction_families
    assert "ion_neutral_followup" in reaction_families
    assert "dissociative_recombination" in reaction_families
    assert "collisional_quenching" in reaction_families
    assert result.metadata["network_manifest"]["promoted_usage"]["count"] >= 1
    assert any(
        reaction.metadata.get("template_origin") == "source_backed_promotion"
        for reaction in result.reactions
    )


def test_user_facing_etch_presets_build_expected_species_and_families():
    cases = {
        "examples/production_blueprint/config_etch_common_support_runtime.yaml": {
            "species": {"Ar+", "O2+", "O2-", "N2+", "Ar[1s5]"},
            "families": {"charge_transfer", "electron_excitation", "ion_neutral_followup"},
            "expect_promoted": False,
        },
        "examples/production_blueprint/config_etch_fluorocarbon_runtime.yaml": {
            "species": {"CF4+", "CF4-", "CHF3+", "CH2F2+", "c-C4F8-", "C2F4+"},
            "families": {"electron_attachment", "electron_ionization", "electron_dissociative_ionization"},
            "expect_promoted": True,
        },
        "examples/production_blueprint/config_etch_inorganic_fluoride_runtime.yaml": {
            "species": {"SF6+", "SF6[A1]", "NF3+", "NF3[A1]", "O2+"},
            "families": {"electron_dissociation", "ion_neutral_followup", "collisional_quenching"},
            "expect_promoted": True,
        },
        "examples/production_blueprint/config_etch_halogen_runtime.yaml": {
            "species": {"Cl2+", "HCl+", "Br2+", "HBr+", "BCl3+", "H2+"},
            "families": {"electron_dissociation", "radical_neutral_reaction", "dissociative_recombination"},
            "expect_promoted": True,
        },
    }

    for config_path, expected in cases.items():
        runtime, species_keys, reaction_families = _build_species_keys_and_families(config_path)
        assert expected["species"].issubset(species_keys), config_path
        assert expected["families"].issubset(reaction_families), config_path
        assert runtime.config.catalog_policy.reaction_conflict_policy == "prefer_higher_priority"
        has_source_backed_templates = "template_promotion:source_backed_templates" in runtime.catalog.loaded_resources
        assert has_source_backed_templates is expected["expect_promoted"], config_path


def test_user_facing_deposition_presets_build_expected_species_and_families():
    cases = {
        "examples/production_blueprint/config_deposition_silane_gas_phase_runtime.yaml": {
            "species": {"SiH4+", "SiH2Cl2+", "SiHCl3+", "SiH2Cl2[A1]", "SiHCl3[B1]"},
            "families": {"electron_dissociation", "ion_neutral_followup", "collisional_quenching"},
        },
        "examples/production_blueprint/config_deposition_reactant_gas_phase_runtime.yaml": {
            "species": {"NH3+", "N2O+", "O3+", "O2[c1Sigma_u_minus]", "H2+"},
            "families": {"electron_attachment", "electron_excitation", "dissociative_recombination"},
        },
    }

    for config_path, expected in cases.items():
        runtime, species_keys, reaction_families = _build_species_keys_and_families(config_path)
        assert expected["species"].issubset(species_keys), config_path
        assert expected["families"].issubset(reaction_families), config_path
        assert runtime.config.catalog_policy.reaction_conflict_policy == "prefer_higher_priority"
        assert "template_promotion:source_backed_templates" in runtime.catalog.loaded_resources
