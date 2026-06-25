from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import numpy as np

from ..repositories import artifacts as artifact_repo
from .artifact_store import get_artifact_store

AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")


def _artifact_key(storage_uri: str) -> str:
    for prefix in ("artifact://", "local://"):
        if storage_uri.startswith(prefix):
            return storage_uri[len(prefix):]
    raise ValueError("unsupported_artifact_storage")


def _normalize_sequence(sequence: str) -> str:
    normalized = "".join(sequence.split()).upper()
    if not normalized:
        raise ValueError("empty_sequence")
    if len(normalized) > 1500:
        raise ValueError("sequence_too_long:max_1500_residues")
    invalid = sorted(set(normalized) - AMINO_ACIDS)
    if invalid:
        raise ValueError(f"invalid_amino_acids:{''.join(invalid)}")
    return normalized


def _global_alignment(left: str, right: str) -> tuple[str, str, int]:
    match, mismatch, gap = 2, -1, -2
    rows, cols = len(left) + 1, len(right) + 1
    score = [[0] * cols for _ in range(rows)]
    trace = [[""] * cols for _ in range(rows)]
    for i in range(1, rows):
        score[i][0] = i * gap
        trace[i][0] = "up"
    for j in range(1, cols):
        score[0][j] = j * gap
        trace[0][j] = "left"
    for i in range(1, rows):
        for j in range(1, cols):
            options = {
                "diag": score[i - 1][j - 1] + (match if left[i - 1] == right[j - 1] else mismatch),
                "up": score[i - 1][j] + gap,
                "left": score[i][j - 1] + gap,
            }
            direction = max(options, key=options.get)
            score[i][j] = options[direction]
            trace[i][j] = direction
    aligned_left: list[str] = []
    aligned_right: list[str] = []
    i, j = len(left), len(right)
    while i or j:
        direction = trace[i][j]
        if direction == "diag":
            aligned_left.append(left[i - 1])
            aligned_right.append(right[j - 1])
            i -= 1
            j -= 1
        elif direction == "up":
            aligned_left.append(left[i - 1])
            aligned_right.append("-")
            i -= 1
        else:
            aligned_left.append("-")
            aligned_right.append(right[j - 1])
            j -= 1
    return "".join(reversed(aligned_left)), "".join(reversed(aligned_right)), score[-1][-1]


def compare_sequences(sequences: list[dict[str, str]]) -> dict[str, Any]:
    normalized = [
        {
            "name": str(item.get("name") or f"sequence_{index + 1}")[:160],
            "sequence": _normalize_sequence(item.get("sequence") or ""),
        }
        for index, item in enumerate(sequences)
    ]
    if sum(len(item["sequence"]) for item in normalized) > 10_000:
        raise ValueError("sequence_set_too_large:max_10000_residues")
    reference = normalized[0]
    alignments = []
    position_votes: list[list[str]] = [[] for _ in reference["sequence"]]
    for item in normalized[1:]:
        aligned_ref, aligned_query, score = _global_alignment(reference["sequence"], item["sequence"])
        matches = sum(
            1 for left, right in zip(aligned_ref, aligned_query, strict=True)
            if left == right and left != "-"
        )
        compared = sum(
            1 for left, right in zip(aligned_ref, aligned_query, strict=True)
            if left != "-" and right != "-"
        )
        ref_index = -1
        for left, right in zip(aligned_ref, aligned_query, strict=True):
            if left != "-":
                ref_index += 1
                if right != "-":
                    position_votes[ref_index].append(right)
        alignments.append({
            "reference": reference["name"],
            "query": item["name"],
            "aligned_reference": aligned_ref,
            "aligned_query": aligned_query,
            "score": score,
            "identity": round(matches / compared, 4) if compared else 0,
            "coverage": round(compared / len(reference["sequence"]), 4),
        })
    conserved_positions = [
        index + 1
        for index, residues in enumerate(position_votes)
        if residues and all(residue == reference["sequence"][index] for residue in residues)
    ]
    return {
        "reference": reference,
        "sequences": [{"name": item["name"], "length": len(item["sequence"])} for item in normalized],
        "alignments": alignments,
        "conserved_reference_positions": conserved_positions,
        "note": "Pairwise global alignment against the selected reference; review structural and functional context before fixing residues.",
    }


def _ca_coordinates(path: Path) -> np.ndarray:
    coordinates = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("ATOM") or line[12:16].strip() != "CA":
            continue
        try:
            coordinates.append([float(line[30:38]), float(line[38:46]), float(line[46:54])])
        except ValueError:
            continue
    if len(coordinates) < 3:
        raise ValueError("structure_requires_at_least_three_ca_atoms")
    return np.asarray(coordinates, dtype=float)


def _kabsch_rmsd(reference: np.ndarray, query: np.ndarray) -> float:
    reference = reference - reference.mean(axis=0)
    query = query - query.mean(axis=0)
    covariance = query.T @ reference
    left, _, right = np.linalg.svd(covariance)
    correction = np.eye(3)
    correction[-1, -1] = -1.0 if np.linalg.det(left @ right) < 0 else 1.0
    rotation = left @ correction @ right
    fitted = query @ rotation
    return float(np.sqrt(np.mean(np.sum((fitted - reference) ** 2, axis=1))))


def compare_structures(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    artifact_ids: list[str],
) -> dict[str, Any]:
    artifacts = []
    for artifact_id in artifact_ids:
        artifact = artifact_repo.get_artifact(connection, artifact_id)
        if artifact is None:
            raise ValueError(f"artifact_not_found:{artifact_id}")
        if artifact.get("project_id") != project_id:
            raise ValueError("artifact_project_mismatch")
        if artifact.get("format") not in {"pdb"}:
            raise ValueError(f"unsupported_structure_format:{artifact.get('format')}")
        artifacts.append(artifact)
    store = get_artifact_store()
    reference = artifacts[0]
    reference_coordinates = _ca_coordinates(
        store.get_local_path(_artifact_key(reference["storage_uri"]))
    )
    comparisons = []
    for artifact in artifacts[1:]:
        coordinates = _ca_coordinates(store.get_local_path(_artifact_key(artifact["storage_uri"])))
        paired_count = min(len(reference_coordinates), len(coordinates))
        comparisons.append({
            "reference_artifact_id": reference["artifact_id"],
            "query_artifact_id": artifact["artifact_id"],
            "reference_name": reference["display_name"],
            "query_name": artifact["display_name"],
            "reference_ca_count": len(reference_coordinates),
            "query_ca_count": len(coordinates),
            "paired_ca_count": paired_count,
            "ca_rmsd": round(
                _kabsch_rmsd(reference_coordinates[:paired_count], coordinates[:paired_count]),
                4,
            ),
            "coverage": round(paired_count / max(len(reference_coordinates), len(coordinates)), 4),
        })
    return {
        "reference_artifact_id": reference["artifact_id"],
        "comparisons": comparisons,
        "note": "CA atoms are paired by file order. Confirm chain and residue mapping before using RMSD as a design gate.",
    }
