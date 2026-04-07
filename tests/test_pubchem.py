from pathlib import Path

from plasma_reaction_builder.adapters import PubChemIdentityAdapter


def test_pubchem_snapshot_lookup():
    path = Path("examples/snapshots/pubchem_identity_snapshot.json")
    adapter = PubChemIdentityAdapter(snapshot_path=str(path), live_api=False)
    record = adapter.resolve("Methane", namespace="name")
    assert record is not None
    assert record.title == "Methane"
    assert record.formula == "CH4"
    assert record.cid == 297


def test_pubchem_snapshot_helpers_use_stable_public_api():
    path = Path("examples/snapshots/pubchem_identity_snapshot.json")
    adapter = PubChemIdentityAdapter(snapshot_path=str(path), live_api=False)
    record = adapter.resolve("Methane", namespace="name")

    assert record is not None
    assert adapter.snapshot_key("name", "Methane") == "name:methane"
    assert adapter.record_to_snapshot_payload(record)["formula"] == "CH4"
