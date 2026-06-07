import pytest
from fastapi import HTTPException

from backend.app.services.artifacts import (
    candidate_structure_path,
    parse_pdb_metadata,
    resolve_artifact_path,
)


SAMPLE_PDB = """\
ATOM      1  N   ALA A   1      11.104   6.134  -6.504  1.00  0.00           N
ATOM      2  CA  ALA A   1      11.639   6.071  -5.147  1.00  0.00           C
ATOM      3  N   GLY B   2      12.104   7.134  -4.504  1.00  0.00           N
"""


def test_parse_pdb_metadata_counts_atoms():
    metadata = parse_pdb_metadata(SAMPLE_PDB)
    assert metadata["atom_count"] == 3
    assert metadata["chain_count"] >= 1


def test_candidate_structure_path_prefers_complex():
    assert candidate_structure_path("mono.pdb", "complex.pdb") == "complex.pdb"
    assert candidate_structure_path("mono.pdb", None) == "mono.pdb"
    assert candidate_structure_path(None, None) is None


def test_resolve_artifact_path_blocks_traversal():
    with pytest.raises(HTTPException) as exc:
        resolve_artifact_path("../../etc/passwd")
    assert exc.value.status_code == 400


def test_resolve_artifact_path_missing_file():
    with pytest.raises(HTTPException) as exc:
        resolve_artifact_path("uploads/does-not-exist-xyz.pdb")
    assert exc.value.status_code == 404
