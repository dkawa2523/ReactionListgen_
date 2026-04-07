from plasma_reaction_builder.adapters import AtctSnapshotAdapter
from plasma_reaction_builder.model import ReactionRecord, SpeciesState


def test_atct_enrich_and_delta_h():
    adapter = AtctSnapshotAdapter("examples/snapshots/atct_snapshot.csv")
    ch4 = SpeciesState(prototype_key="CH4", display_name="Methane", formula="CH4")
    ch3 = SpeciesState(prototype_key="CH3", display_name="Methyl radical", formula="CH3")
    h = SpeciesState(prototype_key="H", display_name="Hydrogen atom", formula="H", state_class="atom")
    assert adapter.enrich_species(ch4)
    assert adapter.enrich_species(ch3)
    assert adapter.enrich_species(h)

    reaction = ReactionRecord(
        key="r1",
        family="radical_fragmentation",
        equation="CH4 -> CH3 + H",
        reactant_state_ids=[ch4.id],
        product_state_ids=[ch3.id, h.id],
        reactant_keys=["CH4"],
        product_keys=["CH3", "H"],
        lhs_tokens=["CH4"],
        rhs_tokens=["CH3", "H"],
        generation=1,
    )
    delta_h = adapter.reaction_delta_h(reaction, {ch4.id: ch4, ch3.id: ch3, h.id: h})
    assert delta_h is not None
    assert delta_h > 0
