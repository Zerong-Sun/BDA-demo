# BDA Workbench Frontend

This directory contains the first static frontend framework for the BDA Workbench MVP.

## Scope

- Local static demo for the PD-1 binder closed loop.
- Four primary views: Experiments, Workflow, Candidates, Results.
- Demo data is isolated in `data/demo-data.js`.
- Future backend contracts are stubbed in `services/api-client.js`.

## Demo Story

- Target: PD-1 binder design.
- Route: RFdiffusion -> ProteinMPNN -> AlphaFold2 -> Rosetta -> BDA filters -> Wet-lab validation.
- Evidence: 9/48 BLI-positive candidates, best BLI Kd 0.6 nM from `PD1Binder_c4361`.
- Round two: preserve the c4361 motif, increase scaffold diversity, and penalize exposed hydrophobic area.

## Run

Open `index.html` directly in a browser, or serve the repository root with any static server.

```sh
python3 -m http.server 4173
```

Then visit `http://localhost:4173/nolab/`.
