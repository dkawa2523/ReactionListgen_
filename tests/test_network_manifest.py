from plasma_reaction_builder.model import BuildResult, ReactionRecord, SpeciesState
from plasma_reaction_builder.network_manifest import build_network_manifest_from_payload, build_result_network_manifest


def test_result_network_manifest_summarizes_fallback_and_promotion_usage():
    result = BuildResult(
        species=[
            SpeciesState(
                prototype_key="O2",
                display_name="Oxygen",
                formula="O2",
                metadata={"state_origin": "state_master"},
            ),
            SpeciesState(
                prototype_key="O2[A1]",
                display_name="Oxygen(A1)",
                formula="O2",
                state_class="excited",
                metadata={"state_origin": "molecular_excited_state"},
            ),
        ],
        reactions=[
            ReactionRecord(
                key="curated::1",
                family="electron_dissociation",
                equation="e- + O2 -> e- + O + O",
                reactant_state_ids=[],
                product_state_ids=[],
                reactant_keys=["O2"],
                product_keys=["O", "O"],
                lhs_tokens=["e-", "O2"],
                rhs_tokens=["e-", "O", "O"],
                generation=1,
                metadata={
                    "template_origin": "curated_catalog",
                    "template_layer": "catalog",
                    "catalog_resource": "catalog_34_reactions_electron_dissociation_oxygen.yaml",
                },
            ),
            ReactionRecord(
                key="promo::1",
                family="electron_excitation",
                equation="e- + O2 -> e- + O2(A1)",
                reactant_state_ids=[],
                product_state_ids=[],
                reactant_keys=["O2"],
                product_keys=["O2[A1]"],
                lhs_tokens=["e-", "O2"],
                rhs_tokens=["e-", "O2(A1)"],
                generation=1,
                metadata={
                    "template_origin": "source_backed_promotion",
                    "template_layer": "promotion",
                    "template_source_system": "qdb",
                },
            ),
        ],
        diagnostics=[],
        metadata={
            "config_sources": ["base.yaml", "runtime.yaml"],
            "catalog_policy": {"reaction_conflict_policy": "prefer_higher_priority"},
        },
    )

    manifest = build_result_network_manifest(result)

    assert manifest["species_count"] == 2
    assert manifest["reaction_count"] == 2
    assert manifest["fallback_usage"]["count"] == 1
    assert manifest["promoted_usage"]["count"] == 1
    assert any(item["name"] == "curated_catalog" for item in manifest["reaction_by_origin"])
    assert any(item["name"] == "source_backed_promotion" for item in manifest["reaction_by_origin"])
    assert any(item["name"] == "qdb" for item in manifest["promoted_usage"]["template_source_systems"])


def test_network_manifest_can_be_rebuilt_from_json_payload():
    payload = {
        "metadata": {
            "config_sources": ["base.yaml", "runtime.yaml"],
            "catalog_policy": {"reaction_conflict_policy": "prefer_higher_priority"},
        },
        "species": [
            {"prototype_key": "Br2", "metadata": {"state_origin": "state_master"}},
        ],
        "reactions": [
            {
                "family": "radical_neutral_reaction",
                "metadata": {
                    "template_origin": "source_backed_promotion",
                    "template_layer": "promotion",
                    "template_source_system": "qdb",
                },
                "evidence": [
                    {"source_system": "qdb", "source_name": "QDB"},
                ],
            }
        ],
    }

    manifest = build_network_manifest_from_payload(payload)

    assert manifest["config_sources"] == ["base.yaml", "runtime.yaml"]
    assert manifest["catalog_policy"]["reaction_conflict_policy"] == "prefer_higher_priority"
    assert manifest["reaction_evidence_source_systems"] == [{"name": "qdb", "count": 1}]
