# SUSTech LSF Protein Design Script Rules

This document fixes the script-generation contract used by BDA Workbench for the sweet-protein RFdiffusion -> ProteinMPNN -> Superfold workflow.

## Submission Flow

1. Edit node parameters in Workbench.
2. Save parameters.
3. Generate the script preview.
4. Review the generated LSF script and input manifest.
5. Upload and submit from the preview action, or download the script and submit it manually.

The backend must regenerate scripts from the saved/previewed node parameters. Copilot drafts may help explain a job, but real cluster submission must go through explicit user confirmation in the UI or an equivalent authenticated API call.

## RFdiffusion

Required behavior:

- Use the node parameters directly for Hydra arguments such as `contigmap.contigs`, `ppi.hotspot_res`, `inference.num_designs`, `diffuser.T`, and `diffuser.partial_T`.
- Write generated PDBs into `output/` and emit `manifest.json` with a `backbone_set` output.
- Keep route labels such as `monellin` and `brazzein` in metadata so candidates remain separable in the UI.

## ProteinMPNN

Required behavior:

- Stage RFdiffusion PDB outputs into `work/pdb`.
- Run `parse_multiple_chains.py`, then `assign_fixed_chains.py`, then `protein_mpnn_run.py`.
- `num_seq_per_target`, `sampling_temp`, `batch_size`, `seed`, `pdb_path_chains`, and `pack_side_chains` must be parameter-driven.
- Default `pack_side_chains` is `true`.
- When side-chain packing is enabled, register `output/packed/*.pdb` as `packed_structure`.
- Register FASTA/score outputs as `sequence_set` and `score_table`, but downstream Superfold should prefer `packed_structure`.

Reference command shape:

```bash
python /work/bme-liz/software/proteinmpnn-main/protein_mpnn_run.py \
  --jsonl_path output/parsed_pdbs.jsonl \
  --chain_id_jsonl output/assigned_pdbs.jsonl \
  --out_folder output \
  --num_seq_per_target "${NUM_SEQ_PER_TARGET}" \
  --sampling_temp "${SAMPLING_TEMP}" \
  --seed "${SEED}" \
  --batch_size "${BATCH_SIZE}" \
  --pack_side_chains "${PACK_SIDE_CHAINS}"
```

## Superfold / AlphaFold2

Required behavior:

- Prefer PDB inputs in this order: `packed_structure`, `structure`, `backbone_set`.
- Use FASTA only when no PDB inputs exist or the user explicitly selects FASTA mode.
- For ProteinMPNN outputs, Superfold input should be `packed/*.pdb`.
- Use singular `--max_recycle`, matching the validated QM reference scripts.
- Parse `reports.txt` into `alphafold2_confidence.csv` with `candidate_id`, `plddt`, `ptm`, and `rmsd_to_input`.
- Register predicted PDBs as `predicted_structure` and insert/update folded candidates.

Reference command shape:

```bash
/work/bme-liz/software/superfold/superfold "${pdb_file}" \
  --models "${SUPERFOLD_MODELS}" \
  --max_recycle "${MAX_RECYCLE}" \
  --output_summary \
  --out_dir "output/${candidate_id}"
```

## Large Packed-PDB Batches

For large batches, avoid one huge `bsub < submit.lsf` job array if the cluster blocks or stalls submission. Use chunked array jobs:

- Recommended chunk size: 50 PDBs.
- Recommended concurrency: 16.
- Submit the first chunk as a smoke batch, then continue after checking `summary.csv` count and `bjobs` RUN/PEND pressure.
- Use a `PDB_OFFSET` variable so the same script can map `LSB_JOBINDEX` to the global sorted PDB list.

Do not use `find | sort | head ...` under `set -o pipefail` for staging input subsets. Write the sorted list to a file first, then select lines. The direct pipe can exit with code `141` because `head` closes the pipe early.

## SSH Transfer Rule

Password-based SSH through `expect` can corrupt raw binary tar streams. Remote workspace upload and output collection must transfer tar archives as base64 text:

```bash
tar -C "${source}" -cf - . | base64
base64 -d | tar -C "${target}" -xf -
```

## UI Guarantees

The Workbench node detail panel must keep this order:

1. Parameter editing.
2. Script generation and review.
3. Copy/download script.
4. Explicit upload and submit.
5. Job status and output collection.

Changing parameters must change the generated script before submission. Submission must use the same override parameters, queue, resource requirement, and GPU requirement shown in the preview panel.
