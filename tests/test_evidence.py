from plasma_reaction_builder.adapters import NistKineticsIndex, QdbEvidenceIndex, ReactionEvidenceAggregator
from plasma_reaction_builder.model import ReactionRecord


def test_evidence_matches_forward_and_reverse():
    aggregator = ReactionEvidenceAggregator(
        [
            NistKineticsIndex.from_json("examples/snapshots/nist_kinetics_snapshot.json"),
            QdbEvidenceIndex.from_json("examples/snapshots/qdb_evidence_snapshot.json"),
        ]
    )

    forward = ReactionRecord(
        key="r1",
        family="electron_ionization",
        equation="e- + CH4 -> e- + e- + CH4+",
        reactant_state_ids=[],
        product_state_ids=[],
        reactant_keys=["CH4"],
        product_keys=["CH4+"],
        lhs_tokens=["e-", "CH4"],
        rhs_tokens=["e-", "e-", "CH4+"],
        generation=1,
    )
    reverse_like = ReactionRecord(
        key="r2",
        family="radical_fragmentation",
        equation="CH4 -> CH3 + H",
        reactant_state_ids=[],
        product_state_ids=[],
        reactant_keys=["CH4"],
        product_keys=["CH3", "H"],
        lhs_tokens=["CH4"],
        rhs_tokens=["CH3", "H"],
        generation=1,
    )

    forward_hits = aggregator.match(forward)
    reverse_hits = aggregator.match(reverse_like)
    assert any(hit.source_system == "qdb" for hit in forward_hits)
    assert any(hit.source_system == "nist_kinetics" for hit in reverse_hits)
