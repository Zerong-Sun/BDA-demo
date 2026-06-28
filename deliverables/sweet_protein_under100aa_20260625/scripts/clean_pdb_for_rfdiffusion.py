#!/usr/bin/env python3
"""Normalize one PDB chain to chain A with contiguous residue numbering."""

from __future__ import annotations

import argparse
from pathlib import Path


def clean_pdb(source: Path, destination: Path, source_chain: str) -> int:
    residue_map: dict[tuple[str, str], int] = {}
    selected_altlocs: set[tuple[str, str, str]] = set()
    output: list[str] = []
    for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("ATOM") or len(line) < 54:
            continue
        if line[21].strip() != source_chain:
            continue
        altloc = line[16].strip()
        atom_name = line[12:16].strip()
        original_residue = (line[22:26].strip(), line[26].strip())
        atom_key = (*original_residue, atom_name)
        if altloc not in {"", "A"} or atom_key in selected_altlocs:
            continue
        selected_altlocs.add(atom_key)
        if original_residue not in residue_map:
            residue_map[original_residue] = len(residue_map) + 1
        new_residue = residue_map[original_residue]
        normalized = (
            f"{line[:16]} "
            f"{line[17:21]}A{new_residue:4d} "
            f"{line[27:]}"
        )
        output.append(normalized)
    if not output:
        raise ValueError(f"no_atoms_for_chain:{source_chain}")
    output.extend(["TER", "END"])
    destination.write_text("\n".join(output) + "\n", encoding="utf-8")
    return len(residue_map)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--chain", required=True)
    args = parser.parse_args()
    count = clean_pdb(args.source, args.destination, args.chain)
    print(f"normalized_residues={count}")


if __name__ == "__main__":
    main()
