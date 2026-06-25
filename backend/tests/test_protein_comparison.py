import numpy as np
import pytest

from backend.app.services.protein_comparison_service import (
    _kabsch_rmsd,
    compare_sequences,
)


def test_compare_sequences_reports_identity_coverage_and_conserved_positions():
    result = compare_sequences([
        {"name": "reference", "sequence": "ACDEFG"},
        {"name": "variant", "sequence": "ACNEFG"},
        {"name": "short", "sequence": "ACDEG"},
    ])

    assert result["reference"]["name"] == "reference"
    assert len(result["alignments"]) == 2
    assert result["alignments"][0]["identity"] == pytest.approx(5 / 6, abs=1e-4)
    assert 1 in result["conserved_reference_positions"]
    assert 3 not in result["conserved_reference_positions"]


def test_compare_sequences_rejects_non_amino_acid_input():
    with pytest.raises(ValueError, match="invalid_amino_acids"):
        compare_sequences([
            {"name": "reference", "sequence": "ACDX"},
            {"name": "variant", "sequence": "ACDE"},
        ])


def test_kabsch_rmsd_is_invariant_to_rigid_transform():
    reference = np.asarray([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ])
    rotation = np.asarray([
        [0.0, -1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
    ])
    query = reference @ rotation + np.asarray([5.0, -2.0, 3.0])

    assert _kabsch_rmsd(reference, query) == pytest.approx(0.0, abs=1e-8)
