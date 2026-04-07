from pathlib import Path

from plasma_reaction_builder.adapters import NistAsdBootstrapAdapter


def test_asd_bootstrap_generates_atomic_states():
    paths = [
        "examples/snapshots/asd/C_I.csv",
        "examples/snapshots/asd/C_II.csv",
        "examples/snapshots/asd/H_I.csv",
        "examples/snapshots/asd/F_I.csv",
    ]
    adapter = NistAsdBootstrapAdapter(paths)
    prototypes = adapter.bootstrap(["CH4", "C4F8"], max_ion_charge=1, max_levels_per_spectrum=2)
    keys = {proto.key for proto in prototypes}
    assert "C" in keys
    assert "C+" in keys
    assert any(key.startswith("C[") for key in keys)
    assert "F" in keys
