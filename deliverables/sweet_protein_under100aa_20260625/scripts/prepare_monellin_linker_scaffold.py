#!/usr/bin/env python3
"""Split modeled MNEI into natural monellin B/A motif chains for linker design."""

from __future__ import annotations

import argparse
from pathlib import Path


def prepare(source: Path, destination: Path) -> None:
    residue_keys: list[tuple[str, str]] = []
    output: list[str] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.startswith("ATOM"):
            continue
        residue_key = (line[21], line[22:27])
        if residue_key not in residue_keys:
            residue_keys.append(residue_key)
        index = residue_keys.index(residue_key) + 1
        if index <= 50:
            chain = "A"
            residue_number = index
        elif index >= 53:
            chain = "B"
            residue_number = index - 52
        else:
            # Remove the existing MNEI Gly-Phe linker. RFdiffusion will rebuild
            # a 2-4 residue linker between the two preserved motifs.
            continue
        rebuilt = (
            f"{line[:21]}{chain}{residue_number:4d}{line[26:]}"
        )
        output.append(rebuilt)
    output.extend(["TER", "END"])
    destination.write_text("\n".join(output) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.destination)


if __name__ == "__main__":
    main()
