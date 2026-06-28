import sqlite3
from pathlib import Path

from backend.app.copilot.tools import execute_tool
from backend.app.plugins.defaults import register_default_model_plugins
from backend.app.repositories import model_catalog
from backend.app.services.script_importer import consistency_report, import_script_tree, parse_script


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    schema = Path(__file__).resolve().parents[1] / "db" / "schema.sql"
    connection.executescript(schema.read_text())
    connection.commit()
    connection.execute("PRAGMA foreign_keys = OFF")
    register_default_model_plugins(connection)
    return connection


def test_parse_lsf_extracts_resources_and_model_parameters(tmp_path):
    script = tmp_path / "run.lsf"
    script.write_text(
        "\n".join([
            "#!/bin/bash",
            "#BSUB -q gpu-test",
            '#BSUB -gpu "num=1"',
            "python run.py \\",
            "inference.input_pdb=target.pdb \\",
            "inference.num_designs=50 \\",
            "--sampling_temp 0.2",
        ])
    )

    parsed = parse_script(script, "qm-scripts/rfd/run.lsf")

    assert parsed["resource_config"]["q"] == "gpu-test"
    keys = {item["parameter_key"] for item in parsed["observations"]}
    assert "inference.num_designs" in keys
    assert "sampling_temp" in keys


def test_import_script_tree_builds_catalog_and_consistency_report(tmp_path):
    root = tmp_path / "qm-scripts" / "mpnn"
    root.mkdir(parents=True)
    (root / "mpnn.lsf").write_text(
        "python protein_mpnn_run.py --num_seq_per_target 10 --sampling_temp 0.5\n"
    )
    connection = _connection()
    try:
        result = import_script_tree(
            connection,
            tmp_path / "qm-scripts",
            repository_root=tmp_path,
        )
        assets = model_catalog.list_script_assets(
            connection,
            model_plugin_id="plugin_proteinmpnn",
        )
        report = consistency_report(
            connection,
            model_plugin_id="plugin_proteinmpnn",
        )
    finally:
        connection.close()

    assert result["scripts_imported"] == 1
    assert assets[0]["relative_path"] == "qm-scripts/mpnn/mpnn.lsf"
    model = report["models"][0]
    assert "num_seq_per_target" in model["matched"]
    assert "sampling_temp" in model["matched"]


def test_copilot_can_inspect_model_parameter_catalog(tmp_path):
    root = tmp_path / "qm-scripts" / "rfd"
    root.mkdir(parents=True)
    (root / "run.lsf").write_text("python run.py inference.num_designs=50\n")
    connection = _connection()
    try:
        import_script_tree(connection, tmp_path / "qm-scripts", repository_root=tmp_path)
        result = execute_tool(
            connection,
            "inspect_model_parameters",
            '{"model_name":"RFdiffusion"}',
            None,
        )
    finally:
        connection.close()

    assert result["model"]["model_plugin_id"] == "plugin_rfdiffusion"
    assert any(item["parameter_key"] == "inference.num_designs" for item in result["parameters"])
    assert "inference.num_designs" in result["consistency"]["matched"]
