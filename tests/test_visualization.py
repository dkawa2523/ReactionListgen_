from __future__ import annotations

from pathlib import Path

from plasma_reaction_builder.visualization import render_visualizations


def test_render_visualizations(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    network_path = repo_root / "examples" / "output_network.json"
    config_path = repo_root / "examples" / "config.yaml"
    output_dir = tmp_path / "visuals"

    artifacts = render_visualizations(
        network_path=str(network_path),
        config_path=str(config_path),
        output_dir=output_dir,
        views=["engineer", "plasma", "datasci", "dictionary", "generated"],
        dpi=90,
        max_reactions_in_graph=60,
    )

    assert artifacts
    assert (output_dir / "visual_manifest.json").exists()
    assert (output_dir / "network" / "engineer_process_dag.png").exists()
    assert (output_dir / "network" / "plasma_bipartite_dag.png").exists()
    assert (output_dir / "network" / "datasci_dataset_summary.png").exists()
    assert (output_dir / "lists" / "generated_species.csv").exists()
    assert (output_dir / "lists" / "dictionary_reaction_templates.csv").exists()
    assert any(artifact.view_id == "generated_state_pages" for artifact in artifacts)
