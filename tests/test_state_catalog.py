from pathlib import Path

import yaml

from plasma_reaction_builder.adapters import NistAsdBootstrapAdapter
from plasma_reaction_builder.catalog import TemplateCatalog
from plasma_reaction_builder.state_catalog import load_state_master, materialize_state_master, materialize_state_master_file


def test_materialize_state_master_file_respects_family_and_charge_window(tmp_path: Path):
    source = Path("examples/production_blueprint/state_master_base.yaml")
    output = tmp_path / "species_materialized.yaml"

    materialize_state_master_file(
        source,
        output_path=output,
        families=["core_plasma", "hydrocarbon"],
        charge_window_min=0,
        charge_window_max=1,
    )

    payload = yaml.safe_load(output.read_text(encoding="utf-8"))
    keys = {item["key"] for item in payload["species"]}

    assert "O" in keys
    assert "O+" in keys
    assert "O-" not in keys
    assert "O++" not in keys
    assert "CH4" in keys
    assert "CH4+" in keys
    assert "CH4-" not in keys


def test_materialized_species_catalog_is_runtime_compatible(tmp_path: Path):
    source = Path("examples/production_blueprint/state_master_base.yaml")
    output = tmp_path / "species_materialized.yaml"

    materialize_state_master_file(
        source,
        output_path=output,
        charge_window_min=-1,
        charge_window_max=1,
    )

    catalog = TemplateCatalog.from_sources([], [output])

    assert "CH4" in catalog.species_library
    assert "c-C4F8" in catalog.species_library


def test_materialize_state_master_includes_curated_excited_states(tmp_path: Path):
    source = Path("examples/production_blueprint/state_master_base.yaml")
    output = tmp_path / "species_materialized.yaml"

    materialize_state_master_file(
        source,
        output_path=output,
        families=["noble_gas", "hydrocarbon"],
        charge_window_min=0,
        charge_window_max=0,
    )

    payload = yaml.safe_load(output.read_text(encoding="utf-8"))
    keys = {item["key"] for item in payload["species"]}

    assert "CH4[V24]" in keys
    assert "CH4[V13]" in keys
    assert "Ar+" not in keys


def test_materialize_state_master_expands_atomic_asd_levels(tmp_path: Path):
    asd_path = tmp_path / "Ar_I.csv"
    asd_path.write_text(
        "\n".join(
            [
                "Spectrum,Configuration,Term,J,Level (eV)",
                "Ar I,3p6,1S,0,0.0000",
                "Ar I,3p5 4s,1s5,,11.5500",
                "Ar I,3p5 4s,1s3,,11.7200",
            ]
        ),
        encoding="utf-8",
    )
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
                "    allowed_charges: [0]",
                "    excitation_policy: atomic_asd",
                "    enabled: true",
            ]
        ),
        encoding="utf-8",
    )

    entries = load_state_master(state_master_path)
    prototypes = materialize_state_master(
        entries,
        charge_window_min=0,
        charge_window_max=0,
        asd=NistAsdBootstrapAdapter([str(asd_path)]),
        asd_max_ion_charge=0,
        asd_max_levels_per_spectrum=3,
    )
    keys = {item.key for item in prototypes}

    assert "Ar" in keys
    assert "Ar[1s5]" in keys
    assert "Ar[1s3]" in keys


def test_materialize_state_master_includes_requested_gas_phase_feedstocks():
    source = Path("examples/production_blueprint/state_master_base.yaml")

    prototypes = materialize_state_master(
        load_state_master(source),
        families=[
            "noble_gas",
            "hydrogen",
            "oxygen",
            "nitrogen",
            "fluorocarbon",
            "chlorine",
            "bromine",
            "boron",
            "silicon",
            "sulfur",
            "tungsten",
            "organosilicon",
        ],
        charge_window_min=-1,
        charge_window_max=1,
    )
    keys = {item.key for item in prototypes}

    assert "He" in keys
    assert "H2" in keys
    assert "CF4" in keys
    assert "CHF3" in keys
    assert "CH2F2" in keys
    assert "CH3F" in keys
    assert "C2F6" in keys
    assert "c-C4F8" in keys
    assert "C5F8" in keys
    assert "SF6" in keys
    assert "NF3" in keys
    assert "Cl2" in keys
    assert "HBr" in keys
    assert "HCl" in keys
    assert "BCl3" in keys
    assert "SiH4" in keys
    assert "NH3" in keys
    assert "N2O" in keys
    assert "O3" in keys
    assert "SiH2Cl2" in keys
    assert "SiHCl3" in keys
    assert "WF6" in keys
    assert "C8H20O4Si" in keys
    assert "CF4+" in keys
    assert "SF6-" in keys
    assert "Cl2-" in keys
