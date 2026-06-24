#!/usr/bin/env python

import os
import glob
import re
from Bio.PDB import PDBParser, Superimposer

# ==== 配置区：按需修改 ====
PACKED_DIR = "/work/bme-sunzr/projects/1103/mpnn/mpnn_outputs2/packed"
OUTPUT_DIR = "/work/bme-sunzr/projects/1103/ros2/inputspdb2ec"
ATOM_NAME  = "CA"    # 使用哪种原子算 RMSD，一般用 CA
OUT_TSV    = "rmsd_all2.tsv"
# ==========================

parser = PDBParser(QUIET=True)

packed_name_re = re.compile(
    r"^binder_(\d+)_seq_(\d+)_packed_(\d+)\.pdb$"
)

def get_all_chain_atoms(struct_path, atom_name="CA"):
    """
    读取一个 PDB 文件中所有链的指定原子，
    返回列表 [(key, atom), ...]
    其中 key = (chain_id, hetflag, resseq, icode)
    """
    structure = parser.get_structure("s", struct_path)
    model = structure[0]

    atoms = []
    for chain in model:
        chain_id = chain.id
        for res in chain:
            if atom_name not in res:
                continue
            hetflag, resseq, icode = res.id
            icode_clean = icode.strip() if isinstance(icode, str) else ""
            key = (chain_id, hetflag, resseq, icode_clean)
            atoms.append((key, res[atom_name]))
    return atoms

def match_atom_lists(ref_atoms, mob_atoms):
    """
    根据 (chain_id, hetflag, resseq, icode) 匹配公共残基的原子
    返回 (ref_list, mob_list, n_common)
    """
    ref_dict = {k: a for k, a in ref_atoms}
    mob_dict = {k: a for k, a in mob_atoms}

    common_keys = sorted(set(ref_dict.keys()) & set(mob_dict.keys()))
    ref_list = [ref_dict[k] for k in common_keys]
    mob_list = [mob_dict[k] for k in common_keys]

    return ref_list, mob_list, len(common_keys)

def main():
    packed_files = sorted(glob.glob(os.path.join(PACKED_DIR, "*.pdb")))
    if not packed_files:
        print(f"[ERROR] No PDB files found in {PACKED_DIR}")
        return

    with open(OUT_TSV, "w") as out:
        out.write("id\tbinder_idx\tseq_in\tseq_out\tpacked_pdb\toutput_pdb\tn_atoms\tRMSD_allchains\n")

        for packed in packed_files:
            base_name = os.path.basename(packed)
            m = packed_name_re.match(base_name)
            if not m:
                print(f"[WARN] Skip {base_name}: name not match pattern binder_x_seq_y_packed_z.pdb")
                continue

            binder_idx = int(m.group(1))
            seq_in     = int(m.group(2))
            # 输出 seq 比输入多 1
            seq_out    = seq_in + 1

            # 在 OUTPUT_DIR 中寻找包含 "binder_{binder_idx}-seq{seq_out}" 的 pdb
            pattern_str = f"*binder_{binder_idx}-seq{seq_out}*.pdb"
            pattern = os.path.join(OUTPUT_DIR, pattern_str)
            candidates = sorted(glob.glob(pattern))

            if not candidates:
                print(f"[WARN] No output match for {base_name} with pattern {pattern_str}")
                continue

            output_pdb = candidates[0]  # 取第一个匹配的
            try:
                ref_atoms = get_all_chain_atoms(packed, ATOM_NAME)
                mob_atoms = get_all_chain_atoms(output_pdb, ATOM_NAME)
            except Exception as e:
                print(f"[WARN] {base_name}: {e}")
                continue

            ref_list, mob_list, n_common = match_atom_lists(ref_atoms, mob_atoms)

            if n_common < 5:
                print(f"[WARN] {base_name}: only {n_common} common atoms, skip")
                continue

            si = Superimposer()
            si.set_atoms(ref_list, mob_list)
            rmsd = si.rms

            out.write(
                f"{os.path.splitext(base_name)[0]}\t"
                f"{binder_idx}\t"
                f"{seq_in}\t"
                f"{seq_out}\t"
                f"{base_name}\t"
                f"{os.path.basename(output_pdb)}\t"
                f"{n_common}\t"
                f"{rmsd:.3f}\n"
            )
            print(f"{base_name}: RMSD_allchains = {rmsd:.3f} over {n_common} atoms")

if __name__ == "__main__":
    main()
