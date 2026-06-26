#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarize AlphaFold outputs across subfolders and compute CA-only RMSD.

Behavior:
  • For each subfolder of a root directory, read *_confidences.json and *_summary_confidences.json when present.
  • Look for exactly one model file per folder: prefer "*_model.cif", otherwise "*_model.pdb".
  • Compute RMSD if either:
      - --ref_pdb_dir is provided: match CIF basename "<name>_model.cif" -> "<name>.pdb" in that directory (case-insensitive), OR
      - --ref_pdb is provided: use that single reference PDB for ALL targets (overrides --ref_pdb_dir).
  • Align using ONLY Cα atoms, and still try *all* chain orderings (permutations) and subsets (if chain counts differ).
  • Residue pairing can be:
      - resseq: by (resseq, icode) intersection (fast; requires numbering consistency)
      - sequence: by sequence alignment (handles different residue numbering; can align best-overlap subsequence)
      - auto: sequence if --ref_pdb is used, else resseq

Requires Biopython + numpy + pandas.
"""
import os
import json
import argparse
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

# Biopython imports
try:
    from Bio.PDB import MMCIFParser, PDBIO, PDBParser, Superimposer
    from Bio.PDB.Polypeptide import is_aa
    from Bio.Data.IUPACData import protein_letters_3to1
except ImportError as e:
    # IMPORTANT: don't swallow the real error silently
    print(f"[ERROR] Biopython import failed: {e}")
    MMCIFParser = PDBIO = PDBParser = Superimposer = None
    is_aa = None
    protein_letters_3to1 = None



# --------------------- IO helpers ---------------------
def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to read JSON {path}: {e}")
        return None


def _find_first_with_suffix(folder: str, suffix: str, *, exclude_suffixes: Optional[Sequence[str]] = None) -> Optional[str]:
    """Return the first filename in `folder` that ends with `suffix` (sorted order),
    skipping any that end with suffixes in `exclude_suffixes`."""
    try:
        names = sorted(os.listdir(folder))
    except FileNotFoundError:
        return None

    for f in names:
        if f.endswith(suffix):
            if exclude_suffixes and any(f.endswith(ex) for ex in exclude_suffixes):
                continue
            return os.path.join(folder, f)
    return None


def _mean_safe(x):
    try:
        arr = np.array(x, dtype=float)
        if arr.size == 0:
            return np.nan
        return float(np.nanmean(arr))
    except Exception:
        return np.nan


# --------------------- Structural utilities ---------------------
def _structure_from_file(tag: str, path: str):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".cif", ".mmcif"):
        parser = MMCIFParser(QUIET=True)
    else:
        parser = PDBParser(QUIET=True)
    return parser.get_structure(tag, path)


def _three_to_one_safe(resname: str) -> str:
    """Convert 3-letter AA code to 1-letter; unknown -> 'X'."""
    if not protein_letters_3to1:
        return "X"
    # protein_letters_3to1 uses keys like "Ala", "Gly", ...
    key = resname.strip().title()
    return protein_letters_3to1.get(key, "X")


def _chain_data(struct):
    """
    Extract per-chain data from first model only.

    Returns dict:
      chain_id -> {
        "keys": [(resseq:int, icode:str), ...]           # numbering keys (standard residues)
        "atoms": [Atom(CA), ...]                         # aligned with keys/seq indices
        "seq":  "ACDE..."                                # aligned with atoms indices
        "key_to_atom": {(resseq,icode): Atom(CA), ...}    # convenience for resseq mode
      }
    """
    if is_aa is None:
        raise ImportError("Biopython (Bio.PDB) is required for RMSD computation.")

    out = {}
    model = next(iter(struct))
    for chain in model:
        keys: List[Tuple[int, str]] = []
        atoms: List = []
        seq_chars: List[str] = []

        for res in chain:
            # Only standard residues and only if CA present
            if getattr(res, "id", ("", "", ""))[0] != " ":
                continue
            if not is_aa(res, standard=True):
                continue
            if "CA" not in res:
                continue

            _, resseq, icode = res.id
            keys.append((int(resseq), str(icode).strip()))
            atoms.append(res["CA"])
            seq_chars.append(_three_to_one_safe(res.get_resname()))

        if atoms:
            out[chain.id] = {
                "keys": keys,
                "atoms": atoms,
                "seq": "".join(seq_chars),
                "key_to_atom": {k: a for k, a in zip(keys, atoms)},
            }
    return out


def _match_atoms_resseq(ref_cd: dict, tgt_cd: dict) -> Tuple[List, List]:
    """Match by (resseq, icode); preserve reference order."""
    ref_atoms, tgt_atoms = [], []
    tgt_map = tgt_cd["key_to_atom"]
    for k, a_ref in zip(ref_cd["keys"], ref_cd["atoms"]):
        a_tgt = tgt_map.get(k)
        if a_tgt is not None:
            ref_atoms.append(a_ref)
            tgt_atoms.append(a_tgt)
    return ref_atoms, tgt_atoms


def _match_atoms_sequence(ref_cd: dict, tgt_cd: dict, max_alignments: int = 5) -> Tuple[List, List]:
    """
    Match by sequence alignment (local). Returns atom lists for positions where
    aligned letters match (and are not X), preserving reference order along the alignment.

    This is robust to different residue numbering and can pick best-overlap subsequences.
    """
    ref_seq = ref_cd["seq"]
    tgt_seq = tgt_cd["seq"]
    if not ref_seq or not tgt_seq:
        return [], []

    # Prefer Bio.Align.PairwiseAligner (modern); fallback to pairwise2 if needed.
    pairs: List[Tuple[int, int]] = []
    best_pairs: List[Tuple[int, int]] = []
    best_len = -1
    best_score = float("-inf")

    try:
        from Bio.Align import PairwiseAligner

        aligner = PairwiseAligner()
        aligner.mode = "local"
        aligner.match_score = 2.0
        aligner.mismatch_score = -1.0
        aligner.open_gap_score = -10.0
        aligner.extend_gap_score = -0.5

        for i, aln in enumerate(aligner.align(ref_seq, tgt_seq)):
            if i >= max_alignments:
                break
            # aln.aligned = (ref_blocks, tgt_blocks)
            ref_blocks, tgt_blocks = aln.aligned
            pairs = []
            for (rs, re), (ts, te) in zip(ref_blocks, tgt_blocks):
                # blocks are same length
                for r_idx, t_idx in zip(range(rs, re), range(ts, te)):
                    aa_r = ref_seq[r_idx]
                    aa_t = tgt_seq[t_idx]
                    if aa_r == aa_t and aa_r != "X":
                        pairs.append((r_idx, t_idx))

            # choose alignment with most matched identical residues; break ties by score
            score = float(getattr(aln, "score", 0.0))
            if len(pairs) > best_len or (len(pairs) == best_len and score > best_score):
                best_len = len(pairs)
                best_score = score
                best_pairs = pairs

    except Exception:
        # Fallback: Bio.pairwise2
        try:
            from Bio import pairwise2

            # localms(match, mismatch, open, extend)
            alns = pairwise2.align.localms(ref_seq, tgt_seq, 2, -1, -10, -0.5)
            for i, (a_ref, a_tgt, score, _b, _e) in enumerate(alns[:max_alignments]):
                pairs = []
                r_i = 0
                t_i = 0
                for ch_r, ch_t in zip(a_ref, a_tgt):
                    if ch_r != "-" and ch_t != "-":
                        if ch_r == ch_t and ch_r != "X":
                            pairs.append((r_i, t_i))
                        r_i += 1
                        t_i += 1
                    elif ch_r != "-" and ch_t == "-":
                        r_i += 1
                    elif ch_r == "-" and ch_t != "-":
                        t_i += 1
                if len(pairs) > best_len or (len(pairs) == best_len and score > best_score):
                    best_len = len(pairs)
                    best_score = score
                    best_pairs = pairs
        except Exception:
            return [], []

    if not best_pairs:
        return [], []

    ref_atoms = [ref_cd["atoms"][r] for r, _t in best_pairs]
    tgt_atoms = [tgt_cd["atoms"][t] for _r, t in best_pairs]
    return ref_atoms, tgt_atoms


def _superimpose_rmsd(ref_atoms: List, tgt_atoms: List) -> Tuple[float, Optional[Tuple[np.ndarray, np.ndarray]], Optional[Superimposer]]:
    """Return (rmsd, (rot,tran), sup_obj) or (inf,None,None) if not enough atoms."""
    if len(ref_atoms) < 3 or len(tgt_atoms) < 3:
        return float("inf"), None, None
    n = min(len(ref_atoms), len(tgt_atoms))
    ref_atoms = ref_atoms[:n]
    tgt_atoms = tgt_atoms[:n]
    sup = Superimposer()
    sup.set_atoms(ref_atoms, tgt_atoms)
    rot, tran = sup.rotran
    return float(sup.rms), (rot, tran), sup


def _resolve_reference_for_model(ref_pdb: Optional[str], ref_dir: Optional[str], model_path: str) -> str:
    """
    Resolve which reference PDB to use for a given model.
    - If ref_pdb provided: return it.
    - Else: use ref_dir rule based on model basename prefix.
    """
    if ref_pdb:
        if not os.path.isfile(ref_pdb):
            raise FileNotFoundError(f"--ref_pdb not found: {ref_pdb}")
        return ref_pdb

    if not ref_dir:
        raise ValueError("No reference provided. Use --ref_pdb or --ref_pdb_dir.")

    # Resolve reference PDB path from model basename
    base = os.path.basename(model_path)
    base_lower = base.lower()
    if base_lower.endswith("_model.cif"):
        prefix = base[:-10]  # strip "_model.cif"
    elif base_lower.endswith("_model.pdb"):
        prefix = base[:-10]  # strip "_model.pdb"
    else:
        prefix = os.path.splitext(base)[0]
    prefix_lower = os.path.splitext(prefix)[0].lower()

    if not os.path.isdir(ref_dir):
        raise FileNotFoundError(f"Reference PDB directory not found: {ref_dir}")

    ref_map = {
        os.path.splitext(f)[0].lower(): os.path.join(ref_dir, f)
        for f in os.listdir(ref_dir)
        if f.lower().endswith(".pdb")
    }
    if prefix_lower not in ref_map:
        raise FileNotFoundError(
            f"No reference PDB found for prefix '{prefix}' -> expected '{prefix_lower}.pdb' in {ref_dir}"
        )
    return ref_map[prefix_lower]


def compute_best_rmsd(
    reference_pdb_path: str,
    target_path: str,
    output_aligned_dir: Optional[str] = None,
    residue_match: str = "sequence",
) -> float:
    """
    Compute the minimum Cα RMSD between a target structure and a reference PDB by trying
    *all* one-to-one chain mappings (and subsets if chain counts differ).

    residue_match:
      - "resseq": match residues by (resseq, icode) intersection within each mapped chain
      - "sequence": match residues by sequence alignment (local), robust to numbering differences
    """
    if Superimposer is None:
        raise ImportError("Biopython (Bio.PDB) is required for RMSD computation.")

    from itertools import permutations, combinations

    ref_struct = _structure_from_file("ref", reference_pdb_path)
    tgt_struct = _structure_from_file("tgt", target_path)

    ref_chain_map = _chain_data(ref_struct)
    tgt_chain_map = _chain_data(tgt_struct)

    if not ref_chain_map or not tgt_chain_map:
        raise ValueError("No usable chains with CA atoms found in one or both structures.")

    ref_chain_ids = sorted(ref_chain_map.keys())
    tgt_chain_ids = sorted(tgt_chain_map.keys())

    R, T = len(ref_chain_ids), len(tgt_chain_ids)
    k = min(R, T)

    # Precompute pairwise matched atoms per chain pair (saves a lot of time)
    pair_cache: Dict[Tuple[str, str], Tuple[List, List]] = {}
    for rc in ref_chain_ids:
        for tc in tgt_chain_ids:
            if residue_match == "resseq":
                ra, ta = _match_atoms_resseq(ref_chain_map[rc], tgt_chain_map[tc])
            else:
                ra, ta = _match_atoms_sequence(ref_chain_map[rc], tgt_chain_map[tc], max_alignments=5)
            pair_cache[(rc, tc)] = (ra, ta)

    best = {"rmsd": float("inf"), "map": None, "rotran": None}

    # All subsets and permutations
    for ref_subset in combinations(ref_chain_ids, k):
        for tgt_subset in combinations(tgt_chain_ids, k):
            for tgt_perm in permutations(tgt_subset, k):
                ref_atoms_all, tgt_atoms_all = [], []
                valid_pairs = 0

                for rc, tc in zip(ref_subset, tgt_perm):
                    ra, ta = pair_cache.get((rc, tc), ([], []))
                    if len(ra) >= 3:
                        ref_atoms_all.extend(ra)
                        tgt_atoms_all.extend(ta)
                        valid_pairs += 1

                if valid_pairs == 0 or len(ref_atoms_all) < 3:
                    continue

                rmsd, rotran, _sup = _superimpose_rmsd(ref_atoms_all, tgt_atoms_all)
                if rmsd < best["rmsd"]:
                    best = {"rmsd": rmsd, "map": list(zip(ref_subset, tgt_perm)), "rotran": rotran}

    if not (best["rmsd"] < float("inf")):
        raise ValueError("Failed to compute RMSD: no chain mapping produced >=3 matched CA pairs.")

    # Optionally write aligned PDB using the best transform
    if output_aligned_dir:
        try:
            os.makedirs(output_aligned_dir, exist_ok=True)
            rot, tran = best["rotran"]
            # Apply transform to the target structure (in-place)
            for atom in tgt_struct.get_atoms():
                atom.transform(rot, tran)

            # Try to rename mapped target chains to match reference IDs (best mapping)
            try:
                best_pairs = list(best["map"] or [])
                if best_pairs:
                    model = next(tgt_struct.get_models())
                    chains_by_id = {ch.id: ch for ch in model}

                    # Temporarily rename mapped target chains to avoid collisions
                    import string
                    pool = list(string.ascii_uppercase + string.ascii_lowercase + string.digits)
                    used = set(chains_by_id.keys())
                    placeholder = {}

                    def next_free_id():
                        for c in pool:
                            if c not in used:
                                used.add(c)
                                return c
                        # very unlikely fallback
                        i = 0
                        while True:
                            cand = f"Z{i}"
                            if cand not in used:
                                used.add(cand)
                                return cand
                            i += 1

                    for rc, tc in best_pairs:
                        ch = chains_by_id.get(tc)
                        if ch is None:
                            continue
                        ph = next_free_id()
                        placeholder[tc] = ph
                        ch.id = ph

                    # Refresh mapping
                    chains_by_id = {ch.id: ch for ch in model}
                    used = set(chains_by_id.keys())

                    # Rename placeholders to reference IDs
                    for rc, tc in best_pairs:
                        ph = placeholder.get(tc)
                        if ph is None:
                            continue
                        # If rc exists (unmapped), move it out of the way
                        if rc in chains_by_id and rc not in placeholder.values():
                            conflict_chain = chains_by_id[rc]
                            new_id = next_free_id()
                            conflict_chain.id = new_id
                            chains_by_id = {ch.id: ch for ch in model}

                        ch = chains_by_id.get(ph)
                        if ch is not None:
                            ch.id = rc
                            chains_by_id = {ch.id: ch for ch in model}

                    # Reorder chains: mapped reference IDs first, then remaining sorted
                    mapped_ref_ids = [rc for rc, _tc in best_pairs]
                    chains_by_id = {ch.id: ch for ch in model}
                    remaining = sorted([cid for cid in chains_by_id.keys() if cid not in mapped_ref_ids])
                    new_order = mapped_ref_ids + remaining
                    model.child_list = [chains_by_id[cid] for cid in new_order if cid in chains_by_id]
            except Exception as e:
                print(f"[WARN] Failed to rename/reorder chains to best mapping order: {e}")

            io = PDBIO()
            io.set_structure(tgt_struct)
            base = os.path.splitext(os.path.basename(target_path))[0]
            ref_base = os.path.splitext(os.path.basename(reference_pdb_path))[0]
            out_name = f"{base}_aligned_to_{ref_base}.pdb"
            out_path = os.path.join(output_aligned_dir, out_name)
            io.save(out_path)
        except Exception as e:
            print(f"[WARN] Failed to write aligned PDB: {e}")

    # Log mapping
    try:
        mapping_str = ", ".join([f"{rc}->{tc}" for rc, tc in (best["map"] or [])])
        print(f"[INFO] Best chain mapping: {mapping_str} | RMSD={best['rmsd']:.3f} Å | match={residue_match}")
    except Exception:
        pass

    return float(best["rmsd"])


def _find_model_file(folder_path: str) -> str:
    """Find a single model file per folder, preferring *model.cif then *model.pdb."""
    # Prefer CIF
    for f in sorted(os.listdir(folder_path)):
        if f.lower().endswith("_model.cif") and not f.startswith("."):
            return os.path.join(folder_path, f)
    # Fallback PDB
    for f in sorted(os.listdir(folder_path)):
        if f.lower().endswith("_model.pdb") and not f.startswith("."):
            return os.path.join(folder_path, f)
    raise FileNotFoundError(f"No '*_model.cif' or '*_model.pdb' file found in folder: {folder_path}")


def process_folder(
    folder_path: str,
    ref_pdb_dir: Optional[str],
    ref_pdb: Optional[str],
    output_aligned_dir: Optional[str],
    residue_match: str,
) -> Optional[dict]:
    """
    Process one folder: read AlphaFold JSONs and (optionally) compute RMSD.
    Returns a dict representing one CSV row, or None if nothing useful found.
    """
    print(f"[INFO] Processing: {folder_path}")
    row = {"Folder": os.path.basename(folder_path)}
    found_any = False

    # 1) Read JSON files (if present)
    conf = _find_first_with_suffix(folder_path, "_confidences.json", exclude_suffixes=["_summary_confidences.json"])
    summ = _find_first_with_suffix(folder_path, "_summary_confidences.json")

    if conf:
        found_any = True
        data = _read_json(conf) or {}
        if "atom_plddts" in data:
            row["avg_atom_plddt"] = _mean_safe(data["atom_plddts"])
        if "pae" in data:
            row["avg_pae"] = _mean_safe(data["pae"])

    if summ:
        found_any = True
        data = _read_json(summ) or {}
        for k in ("chain_iptm", "chain_ptm"):
            if k in data and isinstance(data[k], list):
                for i, val in enumerate(data[k]):
                    row[f"{k}_{i}"] = val
        for k in ("chain_pair_iptm", "chain_pair_pae_min"):
            if k in data and isinstance(data[k], list):
                for i, sub in enumerate(data[k]):
                    if isinstance(sub, list):
                        for j, val in enumerate(sub):
                            row[f"{k}_{i}_{j}"] = val
        if "fraction_disordered" in data:
            fd = data["fraction_disordered"]
            if isinstance(fd, list):
                for i, val in enumerate(fd):
                    row[f"fraction_disordered_{i}"] = val
            else:
                row["fraction_disordered"] = fd

    # 2) RMSD if reference is provided
    if ref_pdb or ref_pdb_dir:
        model_path = _find_model_file(folder_path)
        ref_path = _resolve_reference_for_model(ref_pdb, ref_pdb_dir, model_path)
        rmsd = compute_best_rmsd(
            reference_pdb_path=ref_path,
            target_path=model_path,
            output_aligned_dir=output_aligned_dir,
            residue_match=residue_match,
        )
        row["RMSD"] = rmsd
        found_any = True

    return row if found_any else None


def create_csv_from_folders(
    root_dir: str,
    output_csv: str,
    ref_pdb_dir: Optional[str],
    ref_pdb: Optional[str],
    output_aligned_dir: Optional[str],
    residue_match: str,
) -> None:
    if not os.path.isdir(root_dir):
        raise FileNotFoundError(f"Root directory not found: {root_dir}")

    rows = []
    print("[INFO] Scanning folders...")
    for name in sorted(os.listdir(root_dir)):
        folder_path = os.path.join(root_dir, name)
        if os.path.isdir(folder_path):
            r = process_folder(folder_path, ref_pdb_dir, ref_pdb, output_aligned_dir, residue_match)
            if r:
                rows.append(r)

    if not rows:
        print("[WARN] No usable data found; writing empty CSV header.")
        pd.DataFrame().to_csv(output_csv, index=False)
        return

    df = pd.DataFrame(rows)
    first_cols = [c for c in ["Folder", "avg_atom_plddt", "avg_pae", "RMSD"] if c in df.columns]
    other_cols = [c for c in df.columns if c not in set(first_cols)]
    df = df[first_cols + other_cols]
    df.to_csv(output_csv, index=False)
    print(f"[INFO] Wrote: {output_csv} ({len(df)} rows)")


def parse_args():
    p = argparse.ArgumentParser(description="Summarize AF outputs to CSV and compute CA-only RMSD with chain-permutation alignment.")
    p.add_argument("root_dir", help="Path to root folder containing one subfolder per prediction.")
    p.add_argument("--output_csv", default="af3_results_with_rmsd.csv", help="CSV file to write (default: %(default)s).")

    p.add_argument(
        "--ref_pdb_dir",
        default=None,
        help="Folder containing reference PDBs. For model '<name>_model.cif/pdb', matches '<name>.pdb' in this folder (case-insensitive).",
    )
    p.add_argument(
        "--ref_pdb",
        default=None,
        help="Path to a single reference PDB. If provided, ALL models are aligned to this PDB (overrides --ref_pdb_dir).",
    )
    p.add_argument(
        "--residue_match",
        choices=["auto", "resseq", "sequence"],
        default="auto",
        help="How to pair residues within mapped chains. 'sequence' handles different residue numbering. "
             "'auto' uses 'sequence' when --ref_pdb is set, else 'resseq'.",
    )

    p.add_argument("--output_aligned_dir", default="output_aligned", help="Folder to write aligned PDBs (default: %(default)s).")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.residue_match == "auto":
        residue_match = "sequence" if args.ref_pdb else "resseq"
    else:
        residue_match = args.residue_match

    create_csv_from_folders(
        root_dir=args.root_dir,
        output_csv=args.output_csv,
        ref_pdb_dir=args.ref_pdb_dir,
        ref_pdb=args.ref_pdb,
        output_aligned_dir=args.output_aligned_dir,
        residue_match=residue_match,
    )

#### python summarize_af3_results_with_rmsd_reorder_v2.py ./output --ref_pdb C3_T32-2-9-rebuild3-mini_full.pdb --residue_match sequence
#### python summarize_af3_results_with_rmsd_reorder_v2.py ./output --ref_pdb_dir pdbs --residue_match resseq