# Sweet Protein ProteinMPNN next step

This package designs sequences for the 200 RFdiffusion backbones already generated on the QM cluster:

- Monellin backbones: `/work/bme-sunzr/bda/jobs/job_9ca5d2d649a9/output`
- Brazzein backbones: `/work/bme-sunzr/bda/jobs/job_4de7a7ebdc11/output`

The LSF script keeps the local cluster setup from `qm-scripts/mpnn/mpnn1.lsf`:

- Conda env: `/work/bme-liz/miniconda3/envs/mlfold`
- ProteinMPNN: `/work/bme-liz/software/proteinmpnn-main`
- Designed chain: `A`
- Sequences per backbone: `5`
- Sampling temperature: `0.2`

Run on QM after upload:

```bash
cd /work/bme-sunzr/bda/proteinmpnn_sweetprotein_20260627
bsub < submit_proteinmpnn_5seq.lsf
```

Expected outputs:

- `outputs_temp0.2_5seq/seqs/*.fa`
- `outputs_temp0.2_5seq/packed/*.pdb` when side-chain packing succeeds
- `outputs_temp0.2_5seq/sweetprotein_mpnn5_designs.fasta`
- `outputs_temp0.2_5seq/sweetprotein_mpnn5_manifest.json`
