#!/usr/bin/env python3
"""
split_pdb_chain.py

Process all .pdb files in an input folder. Assumes coordinates are only in chain A.
Splits residues as:
  - Chain A: residues 1–108 (keeps original residue numbers)
  - Chain B: residues 109+ (renumbered starting from 1, sequential by appearance)

Writes modified PDBs to an output folder.

Notes:
- Modifies coordinate-like records: ATOM, HETATM, ANISOU, SIGATM, SIGUIJ
- Keeps atom serial numbers unchanged
- Removes any existing TER records and writes a single TER at the end
- Preserves header and post-coordinate records (e.g., CONECT), and writes a single END
- Assumes a single-model PDB (no MODEL/ENDMDL handling)
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

COORD_RECS = {"ATOM  ", "HETATM", "ANISOU", "SIGATM", "SIGUIJ"}
TER_REC = "TER   "
END_RECS = {"END   ", "ENDMDL"}  # we'll rewrite END at the end


def _safe_int(field: str) -> Optional[int]:
    try:
        return int(field)
    except Exception:
        return None


def _set_chain_and_resseq(line: str, chain: str, resseq: int) -> str:
    # Work with fixed-width PDB line; pad to at least 80 chars (common)
    base = line.rstrip("\n")
    chars = list(base.ljust(80))

    # Chain ID at column 22 (1-based) => index 21 (0-based)
    if len(chars) <= 21:
        chars.extend([" "] * (22 - len(chars)))
    chars[21] = chain

    # Residue sequence number at columns 23-26 => indices 22:26
    res_field = f"{resseq:4d}"  # right-aligned width 4
    if len(chars) < 26:
        chars.extend([" "] * (26 - len(chars)))
    chars[22:26] = list(res_field)

    return "".join(chars).rstrip() + "\n"


def _split_segments(lines: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """
    Split file into:
      pre  : before first coordinate/TER record
      coord: consecutive coordinate/TER records
      post : everything after coordinate section ends
    """
    pre: List[str] = []
    coord: List[str] = []
    post: List[str] = []

    started = False
    ended = False

    for line in lines:
        rec = (line[0:6] if len(line) >= 6 else line).ljust(6)
        is_coordish = (rec in COORD_RECS) or (rec == TER_REC)

        if not started:
            if is_coordish:
                started = True
                coord.append(line)
            else:
                pre.append(line)
        elif not ended:
            if is_coordish:
                coord.append(line)
            else:
                ended = True
                post.append(line)
        else:
            post.append(line)

    return pre, coord, post


def _make_ter(last_coord_line: str, serial: int) -> str:
    """
    Create a TER line using the residue name / chain / resseq / icode
    from the last coordinate-like line (ATOM/HETATM/ANISOU/...).
    """
    base = last_coord_line.rstrip("\n").ljust(80)

    resname = base[17:20]  # columns 18-20
    chain = base[21]       # column 22
    resseq = base[22:26]   # columns 23-26
    icode = base[26]       # column 27

    serial = max(1, min(serial, 99999))
    # Format per PDB fixed columns:
    # 1-6  "TER   "
    # 7-11 serial
    # 12-17 blanks
    # 18-20 resname
    # 21   blank
    # 22   chain
    # 23-26 resseq
    # 27   icode
    ter = f"{TER_REC}{serial:5d}      {resname} {chain}{resseq}{icode}\n"
    return ter


def process_pdb_text(lines: List[str], split_after: int = 108) -> List[str]:
    pre, coord, post = _split_segments(lines)

    # Clean post: remove END/ENDMDL; we'll add a single END at the end
    cleaned_post = []
    for line in post:
        rec = (line[0:6] if len(line) >= 6 else line).ljust(6)
        if rec in END_RECS:
            continue
        cleaned_post.append(line)

    out_coord: List[str] = []

    # Mapping for chain B residue renumbering by (old_resseq, icode)
    b_map: Dict[Tuple[int, str], int] = {}
    next_b = 1

    last_serial: Optional[int] = None
    last_written_coord_line: Optional[str] = None

    for line in coord:
        rec = (line[0:6] if len(line) >= 6 else line).ljust(6)

        if rec == TER_REC:
            # Drop all existing TERs; we'll add one at the end
            continue

        if rec not in COORD_RECS:
            # Unexpected in coord segment; keep as-is
            out_coord.append(line)
            continue

        base = line.rstrip("\n").ljust(80)
        chain = base[21]
        old_resseq = _safe_int(base[22:26])
        icode = base[26]

        # Parse serial if present
        serial = _safe_int(base[6:11])
        if serial is not None:
            last_serial = serial

        if chain == "A" and old_resseq is not None:
            if old_resseq <= split_after:
                new_chain = "A"
                new_resseq = old_resseq
            else:
                new_chain = "B"
                key = (old_resseq, icode)
                if key not in b_map:
                    b_map[key] = next_b
                    next_b += 1
                new_resseq = b_map[key]

            new_line = _set_chain_and_resseq(line, new_chain, new_resseq)
            out_coord.append(new_line)
            last_written_coord_line = new_line
        else:
            # Not chain A or missing residue number: leave untouched
            out_coord.append(line)
            if rec in COORD_RECS:
                last_written_coord_line = line

    # Add a final TER (safe: serial+1 won't collide because it's after last atom)
    if last_written_coord_line is not None:
        ter_serial = (last_serial + 1) if last_serial is not None else 1
        out_coord.append(_make_ter(last_written_coord_line, ter_serial))

    # Ensure END at end
    return pre + out_coord + cleaned_post + ["END\n"]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Split chain A in PDBs into chain A (1-108) and chain B (109+ renumbered from 1)."
    )
    ap.add_argument("-i", "--input", required=True, type=Path, help="Input folder containing .pdb files")
    ap.add_argument("-o", "--output", required=True, type=Path, help="Output folder to write modified .pdb files")
    ap.add_argument("--split-after", type=int, default=108, help="Last residue number to keep in chain A (default: 108)")
    ap.add_argument("--glob", default="*.pdb", help="Glob pattern for input files (default: *.pdb)")
    args = ap.parse_args()

    in_dir: Path = args.input
    out_dir: Path = args.output
    split_after: int = args.split_after
    pattern: str = args.glob

    if not in_dir.is_dir():
        raise SystemExit(f"Input path is not a directory: {in_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)

    pdb_files = sorted(in_dir.glob(pattern))
    if not pdb_files:
        raise SystemExit(f"No files matched {pattern} in {in_dir}")

    for pdb_path in pdb_files:
        text = pdb_path.read_text(errors="replace").splitlines(keepends=True)
        new_lines = process_pdb_text(text, split_after=split_after)
        out_path = out_dir / pdb_path.name
        out_path.write_text("".join(new_lines))
        print(f"Wrote: {out_path}")

    print("Done.")


if __name__ == "__main__":
    main()
