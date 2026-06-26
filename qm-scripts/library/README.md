# QM cluster script library

This directory replaces copy-and-edit example scripts with a validated,
source-traceable job generator.

## What is covered

- RFdiffusion: every key in the official `config/inference/base.yaml`.
- ProteinMPNN: every argument in the official `protein_mpnn_run.py`.
- AlphaFold 2 and AlphaFold 3: every flag in the official run entrypoint.
- Boltz: every `boltz predict` option.
- Chai-1: every argument exposed by `chai_lab.chai1.run_inference`.
- BindCraft: target settings, advanced settings, and all default filter keys.
- Rosetta: the supported BDA workflows (`rosetta_scripts`, `relax`,
  `InterfaceAnalyzer`, and `cartesian_ddg`) and their commonly required flags.
- Mask RGN: every Hydra key in the local inference, model, and data configs.

The catalog records the exact upstream Git commit used for extraction. RFdiffusion
checkpoint configuration may override values shown in `base.yaml`; the catalog
therefore treats these as declared configuration defaults, not guaranteed runtime
defaults.

## Fast use

```bash
cd qm-scripts/library

# See models and parameter counts.
python qm_job.py models

# Search/list every available parameter for one model.
python qm_job.py params rfdiffusion
python qm_job.py params proteinmpnn | less

# Copy one example, edit only that JSON, validate and render.
cp examples/rfdiffusion-binder.json my-rfd-job.json
python qm_job.py validate my-rfd-job.json
python qm_job.py render my-rfd-job.json --output jobs/my-rfd-job

# Upload the complete bundle. This does not submit automatically.
bash upload_to_cluster.sh jobs/my-rfd-job qm

# Submit only after reviewing the returned command.
ssh qm "cd /work/bme-sunzr/bda/qm-script-library/my-rfd-job && bsub < submit.lsf"
```

Every validation, render, upload, and cluster runtime error prints:

```text
[BDA_FIX_PATH] /absolute/path/to/the/config/to-edit.json
```

The generated cluster script additionally prints `BDA_JOB_SCRIPT` and
`BDA_LOG_DIR`.

## Configuration shape

```json
{
  "model": "rfdiffusion",
  "executable": "/absolute/path/to/upstream/entrypoint",
  "scheduler": {
    "job_name": "rfd-binder",
    "queue": "4v100-16-e5",
    "cpus": 1,
    "gpus": 1
  },
  "setup": [
    "module purge",
    "source activate /path/to/environment"
  ],
  "parameters": {}
}
```

Only keys present in `catalog.json` are accepted. Set `"include_defaults": true`
only when you intentionally want every non-null upstream default written to the
command line; normally it is safer to pass only explicit overrides.

## Refreshing from upstream

The committed catalog is reproducible from pinned Git revisions:

```bash
python build_catalog.py --clone-root /tmp/bda-qm-upstreams
```

To update a model, first review its current upstream entrypoint/config, update the
commit in `build_catalog.py`, regenerate `catalog.json`, inspect the diff, and run
the tests. Never silently track a moving `main` branch on the cluster.
