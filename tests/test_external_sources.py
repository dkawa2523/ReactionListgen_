from plasma_reaction_builder.adapters import KidaNetworkIndex, ReactionEvidenceFactory, UmistRate22Index, VamdcXsamsIndex
from plasma_reaction_builder.config import EvidenceSourceSpec


def test_umist_ratefile_parses_and_filters_special_processes():
    index = UmistRate22Index.from_ratefile("examples/snapshots/umist_rate22_sample.rates")
    equations = {(" + ".join(entry.reactants), " + ".join(entry.products)) for entry in index.entries}
    assert ("CH3 + H", "CH4") in equations
    assert all("PHOTON" not in entry.reactants for entry in index.entries)


def test_kida_network_parses_simple_reactions():
    index = KidaNetworkIndex.from_file("examples/snapshots/kida_gas_reactions_sample.txt")
    equations = {(" + ".join(entry.reactants), " + ".join(entry.products)) for entry in index.entries}
    assert ("CH3 + H", "CH4") in equations
    assert all("Photon" not in entry.reactants for entry in index.entries)


def test_vamdc_xsams_parses_collision_process():
    index = VamdcXsamsIndex.from_path(
        "examples/snapshots/vamdc_ideadb_sample.xsams",
        source_name="IDEADB (illustrative)",
        source_system="ideadb",
    )
    assert any(entry.reactants == ["e-", "CH4"] and entry.products == ["H-", "CH3"] for entry in index.entries)


def test_reaction_evidence_factory_builds_mixed_indexes():
    factory = ReactionEvidenceFactory()
    indexes = factory.build_indexes(
        [
            EvidenceSourceSpec(kind="umist_ratefile", path="examples/snapshots/umist_rate22_sample.rates"),
            EvidenceSourceSpec(kind="kida_network", path="examples/snapshots/kida_gas_reactions_sample.txt"),
            EvidenceSourceSpec(kind="vamdc_xsams", path="examples/snapshots/vamdc_ideadb_sample.xsams", source_system="ideadb"),
        ]
    )
    assert len(indexes) == 3
    assert sum(len(index.entries) for index in indexes) >= 4


def test_vamdc_query_expands_from_feed_formulas():
    factory = ReactionEvidenceFactory()
    queries = factory.expand_vamdc_queries(
        EvidenceSourceSpec(kind="vamdc_live", url="https://example.invalid", use_feed_formulas=True),
        feed_formulas=["CH4", "C4F8"],
    )
    assert queries == [
        "SELECT * WHERE MoleculeStoichiometricFormula = 'CH4'",
        "SELECT * WHERE MoleculeStoichiometricFormula = 'C4F8'",
    ]
