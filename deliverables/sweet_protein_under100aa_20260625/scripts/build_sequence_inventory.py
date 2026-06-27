#!/usr/bin/env python3
"""Build reusable sequence inventories and pairwise alignment inputs."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEQUENCE_DIR = ROOT / "sequences"
ANALYSIS_DIR = ROOT / "analysis"


def read_fasta(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    header = ""
    sequence: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(">"):
            if header:
                records.append((header, "".join(sequence)))
            header = line[1:]
            sequence = []
        else:
            sequence.append(line.strip())
    if header:
        records.append((header, "".join(sequence)))
    return records


def main() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    selected = {
        "2O9U.fasta": "single-chain monellin MNEI",
        "4HE7.fasta": "brazzein",
        "2DS2.fasta": "mabinlin-2 chains",
        "2DPF.fasta": "curculin-1",
    }
    rows = []
    combined = []
    for filename, label in selected.items():
        for index, (header, sequence) in enumerate(read_fasta(SEQUENCE_DIR / filename), start=1):
            record_id = f"{label.replace(' ', '_')}_{index}"
            rows.append({
                "record_id": record_id,
                "protein_group": label,
                "source_file": filename,
                "length_aa": len(sequence),
                "under_100_aa": len(sequence) < 100,
                "cysteine_count": sequence.count("C"),
                "sequence": sequence,
                "source_header": header,
            })
            combined.append(f">{record_id}|{header}\n{sequence}\n")
    with (ANALYSIS_DIR / "sequence_inventory.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    (ANALYSIS_DIR / "comparison_input.fasta").write_text(
        "".join(combined),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
