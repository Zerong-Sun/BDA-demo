# Local model workspace

This directory is reserved for local or cluster-mounted model source trees,
checkpoints, training outputs, and third-party repositories.

Its contents are intentionally excluded from Git because model repositories may
have separate licenses and histories, while checkpoints and run outputs are
often hundreds of megabytes or larger.

The platform-owned integration boundary lives in:

- `docker/models/<model>/Dockerfile`
- `docker/models/<model>/run.py`
- `backend/app/plugins/defaults.py`

Install external models under this directory only for local development:

```text
models/
├── rfdiffusion/
├── proteinmpnn/
└── maskrgnn/
```

Production deployments should mount model code and checkpoints from a
versioned image, shared filesystem, or object store. Do not commit nested
`.git/` directories, checkpoints, training outputs, scheduler logs, or private
datasets to this repository.
