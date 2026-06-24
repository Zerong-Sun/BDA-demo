from subprocess import CompletedProcess

import httpx
import pytest

from backend.app.copilot import cluster, research


def test_calculate_sequence_properties():
    result = research.calculate_sequence_properties("ACDEFGHIKLMNPQRSTVWY")

    assert result["length"] == 20
    assert result["molecular_weight_da"] > 2000
    assert result["cysteine_count"] == 1
    assert 0 < result["hydrophobic_fraction"] < 1


def test_sequence_properties_reject_invalid_residues():
    with pytest.raises(ValueError, match="invalid_amino_acids"):
        research.calculate_sequence_properties("ACDX")


def test_search_literature_normalizes_results(monkeypatch):
    payload = {
        "hitCount": 1,
        "resultList": {
            "result": [{
                "source": "MED",
                "id": "123",
                "title": "Protein design paper",
                "authorString": "A. Author",
                "pubYear": "2026",
                "doi": "10.1/example",
                "pmid": "123",
                "isOpenAccess": "Y",
                "abstractText": "Abstract.",
            }]
        },
    }

    def handler(request: httpx.Request):
        return httpx.Response(200, json=payload, request=request)

    monkeypatch.setattr(
        research,
        "_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = research.search_literature("protein design")

    assert result["total"] == 1
    assert result["results"][0]["is_open_access"] is True
    assert result["results"][0]["url"].endswith("/MED/123")


def test_cluster_draft_requires_confirmation_and_blocks_dangerous_commands(tmp_path, monkeypatch):
    monkeypatch.setattr(cluster, "DRAFTS_ROOT", tmp_path)
    draft = cluster.create_draft(
        project_id="proj_test",
        created_by="user_test",
        job_name="safe-test",
        command="python analysis.py --input input/test.pdb --output output/result.csv",
        queue="v3-64",
        cpu_count=2,
        expected_outputs=["output/result.csv"],
    )

    assert draft["status"] == "awaiting_confirmation"
    assert "#BSUB -q v3-64" in draft["script"]
    assert "python analysis.py" in draft["script"]

    with pytest.raises(ValueError, match="blocked_cluster_command"):
        cluster.create_draft(
            project_id=None,
            created_by="user_test",
            job_name="unsafe",
            command="sudo rm -rf /",
        )


def test_confirm_cluster_draft_submits_exact_saved_script(tmp_path, monkeypatch):
    monkeypatch.setattr(cluster, "DRAFTS_ROOT", tmp_path)
    draft = cluster.create_draft(
        project_id=None,
        created_by="copilot",
        job_name="confirm-test",
        command="python analysis.py",
    )
    calls = []

    def fake_ssh(command: str, *, input_text=None, check=True):
        calls.append((command, input_text))
        if "bsub < submit.lsf" in command:
            return CompletedProcess([], 0, stdout="Job <12345> is submitted.", stderr="")
        return CompletedProcess([], 0, stdout="", stderr="")

    monkeypatch.setattr(cluster, "_ssh", fake_ssh)
    submitted = cluster.submit_draft(draft["draft_id"], confirmed_by="user_test")

    assert submitted["status"] == "submitted"
    assert submitted["external_id"] == "12345"
    assert any(input_text == draft["script"] for _, input_text in calls)
