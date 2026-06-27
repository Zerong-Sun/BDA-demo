# RFdiffusion round 1: 100 + 100 backbone pilot

## Main route: monellin single-chain linker scaffolding

- Input motifs: natural monellin chain B (50 modeled residues) and chain A
  (44 modeled residues), reconstructed from RCSB 2O9U/MNEI.
- Existing MNEI Gly-Phe linker is removed from the input motif file.
- Contig: `[A1-50/2-4/B1-44]`.
- Output: one continuous 96–98 residue chain.
- Designs: 100.
- `diffuser.T=50`, `diffuser.partial_T=0`.
- CA/frame noise: `0.5/0.5`.

`partial_T=0` is intentional: RFdiffusion partial diffusion requires the
generated contig to have exactly the same length as the input, which conflicts
with sampling a 2–4 residue linker between two motif chains.

The validated MNEI Gly-Phe linker is the reference. Linkers of length 2–4 are
sampled in the pilot to test whether a nearby geometry improves foldability
without exceeding the `<100 aa` project constraint.

## Parallel route: brazzein conservative diversification

- Input: cleaned RCSB 4HE7, 53 modeled residues.
- Contig: `[A1-53]`.
- Designs: 100.
- `diffuser.T=50`, `diffuser.partial_T=5`.
- CA/frame noise: `0.5/0.5`.
- `contigmap.provide_seq=[2,14,20,24,35,45,47,50]` preserves the eight
  zero-indexed modeled cysteine positions used by the four-disulfide scaffold.

## Surface positive charge

RFdiffusion generates backbone geometry, not reliable side-chain sequences.
Position-specific positive-surface design is therefore saved as an explicit
ProteinMPNN/downstream constraint in
`inputs/mpnn_surface_charge_constraints.json`.

The first sequence round should preserve multiple electrostatic families.
Global overcharging is rejected because published MNEI mutagenesis shows that
some positive substitutions increase sweetness while others reduce it.

## Selection after the jobs finish

For each route, retain lineage for all 100 outputs and rank without deleting
failed candidates:

1. output length and single-chain continuity;
2. motif RMSD and linker geometry for monellin;
3. cysteine geometry and disulfide feasibility for brazzein;
4. backbone compactness, clashes, and secondary-structure consistency;
5. diversity clustering before ProteinMPNN.
