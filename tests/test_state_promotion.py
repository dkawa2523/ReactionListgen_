from plasma_reaction_builder.excited_state_registry import ExcitedStateRegistry
from plasma_reaction_builder.formula import parse_species_token
from plasma_reaction_builder.normalization import AliasResolver
from plasma_reaction_builder.runtime import build_runtime


def test_parse_species_token_supports_bracket_excited_labels():
    parsed = parse_species_token("CH4[V14]")
    assert parsed.formula == "CH4"
    assert parsed.excitation_label == "V14"
    assert parsed.state_class == "excited"


def test_parse_species_token_supports_halogen_and_silicon_cations():
    hbr = parse_species_token("HBr+")
    hcl = parse_species_token("HCl+")
    sih2cl2 = parse_species_token("SiH2Cl2+")

    assert hbr.formula == "HBr"
    assert hbr.charge == 1
    assert hbr.state_class == "cation"
    assert hcl.formula == "HCl"
    assert hcl.charge == 1
    assert hcl.state_class == "cation"
    assert sih2cl2.formula == "SiH2Cl2"
    assert sih2cl2.charge == 1
    assert sih2cl2.state_class == "cation"


def test_alias_resolver_normalizes_excited_state_synonyms_from_registry():
    registry = ExcitedStateRegistry.from_path("examples/production_blueprint/excited_state_registry.yaml")
    resolver = AliasResolver(alias_map={}, excited_state_registry=registry)

    assert resolver.canonicalize_token("O2(c^1Σ_u-)", source_system="vamdc") == "O2[c1Sigma_u_minus]"
    assert resolver.canonicalize_token("N2(B^3Π_g)", source_system="ideadb") == "N2[B3Pi_g]"
    assert resolver.canonicalize_token("CH4(v14)", source_system="qdb") == "CH4[V14]"


def test_runtime_promotes_molecular_excited_states_from_external_sources():
    runtime = build_runtime(
        "examples/production_blueprint/config_state_promotion_runtime.yaml",
        include_evidence_indexes=False,
    )

    assert "CH4[V14]" in runtime.catalog.species_library
    assert "O2[c1Sigma_u_minus]" in runtime.catalog.species_library
    assert "N2[B3Pi_g]" in runtime.catalog.species_library
    assert "state_promotion:molecular_excited_states" in runtime.catalog.loaded_resources

    ch4_v14 = runtime.catalog.species_library["CH4[V14]"]
    o2_c = runtime.catalog.species_library["O2[c1Sigma_u_minus]"]
    n2_b = runtime.catalog.species_library["N2[B3Pi_g]"]

    assert ch4_v14.metadata["source_system"] == "qdb"
    assert o2_c.metadata["source_system"] in {"qdb", "vamdc"}
    assert n2_b.metadata["source_system"] == "ideadb"
    assert ch4_v14.metadata["state_origin"] == "source_backed_state_promotion"
    assert o2_c.metadata["state_origin"] == "source_backed_state_promotion"
    assert n2_b.metadata["state_origin"] == "source_backed_state_promotion"
    assert ch4_v14.metadata["registry_canonical_key"] == "CH4[V14]"
    assert o2_c.metadata["registry_canonical_key"] == "O2[c1Sigma_u_minus]"
    assert n2_b.metadata["registry_canonical_key"] == "N2[B3Pi_g]"


def test_runtime_promotes_precursor_excited_states_from_external_sources():
    runtime = build_runtime(
        "examples/production_blueprint/config_excited_precursor_template_promotion_runtime.yaml",
        include_evidence_indexes=False,
    )

    assert "state_promotion:molecular_excited_states" in runtime.catalog.loaded_resources
    assert "BCl3[A1]" in runtime.catalog.species_library
    assert "SiH2Cl2[A1]" in runtime.catalog.species_library
    assert "SiHCl3[B1]" in runtime.catalog.species_library
    assert "C8H20O4Si[Ryd1]" in runtime.catalog.species_library

    bcl3_a1 = runtime.catalog.species_library["BCl3[A1]"]
    sih2cl2_a1 = runtime.catalog.species_library["SiH2Cl2[A1]"]
    sihcl3_b1 = runtime.catalog.species_library["SiHCl3[B1]"]
    teos_ryd1 = runtime.catalog.species_library["C8H20O4Si[Ryd1]"]

    assert bcl3_a1.metadata["source_system"] == "qdb"
    assert sih2cl2_a1.metadata["source_system"] == "qdb"
    assert sihcl3_b1.metadata["source_system"] == "qdb"
    assert teos_ryd1.metadata["source_system"] == "qdb"
    assert bcl3_a1.metadata["state_origin"] == "source_backed_state_promotion"
    assert sih2cl2_a1.metadata["state_origin"] == "source_backed_state_promotion"
    assert sihcl3_b1.metadata["state_origin"] == "source_backed_state_promotion"
    assert teos_ryd1.metadata["state_origin"] == "source_backed_state_promotion"
    assert bcl3_a1.metadata["registry_canonical_key"] == "BCl3[A1]"
    assert sih2cl2_a1.metadata["registry_canonical_key"] == "SiH2Cl2[A1]"
    assert sihcl3_b1.metadata["registry_canonical_key"] == "SiHCl3[B1]"
    assert teos_ryd1.metadata["registry_canonical_key"] == "C8H20O4Si[Ryd1]"


def test_runtime_promotes_fluoride_precursor_excited_states_from_external_sources():
    runtime = build_runtime(
        "examples/production_blueprint/config_excited_fluoride_precursor_template_promotion_runtime.yaml",
        include_evidence_indexes=False,
    )

    assert "state_promotion:molecular_excited_states" in runtime.catalog.loaded_resources
    assert "SF6[A1]" in runtime.catalog.species_library
    assert "NF3[A1]" in runtime.catalog.species_library
    assert "WF6[B1]" in runtime.catalog.species_library

    sf6_a1 = runtime.catalog.species_library["SF6[A1]"]
    nf3_a1 = runtime.catalog.species_library["NF3[A1]"]
    wf6_b1 = runtime.catalog.species_library["WF6[B1]"]

    assert sf6_a1.metadata["source_system"] == "qdb"
    assert nf3_a1.metadata["source_system"] == "qdb"
    assert wf6_b1.metadata["source_system"] == "qdb"
    assert sf6_a1.metadata["state_origin"] == "source_backed_state_promotion"
    assert nf3_a1.metadata["state_origin"] == "source_backed_state_promotion"
    assert wf6_b1.metadata["state_origin"] == "source_backed_state_promotion"
    assert sf6_a1.metadata["registry_canonical_key"] == "SF6[A1]"
    assert nf3_a1.metadata["registry_canonical_key"] == "NF3[A1]"
    assert wf6_b1.metadata["registry_canonical_key"] == "WF6[B1]"
