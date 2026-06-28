# AI 甜味蛋白研发

开发一个长度严格小于100 aa、结构简单、尽量为单链、适合饮料应用的AI甜味蛋白。必须检索、下载并比较 monellin（优先single-chain monellin）、brazzein、mabinlin、pentadin、curculin 的天然序列和可用结构；记录每个候选的链组成、成熟肽长度、二硫键、结构证据、受体机制、表达与稳定性风险。优先天然骨架定向改造，不把预测结合当作甜味或安全证据。输出可编辑的RFdiffusion/ProteinMPNN/结构预测/Rosetta流程，以及表达纯化、人源TAS1R2/TAS1R3功能、感官、食品基质和安全法规实验计划。

## Assumptions
- receptor_species: human (needs_confirmation)
- receptor: TAS1R2/TAS1R3 (working_assumption)
- first_application: beverage (recommended_default)
- automation: confirm_each_compute_node (safe_default)

## Findings
- [pending_review] **Prefer constrained redesign before de novo**: Preserve validated folds, disulfides, and functional residues during partial diffusion or sequence redesign. Treat de novo receptor binders as a high-risk second-generation route.
- [pending_review] **Evidence ladder**: Expression and folding, human receptor activation, sensory confirmation, food-matrix performance, process economics, safety, and regulatory evidence are separate gates.
- [pending_review] **Design and fermentation must be co-optimized**: Rank candidates using effective sweetness titer: protein titer × correctly folded fraction × relative sweetness, rather than expression or docking score alone.
- [pending_review] **First-generation scaffold priority**: Single-chain monellin and brazzein-53/54 are the default first-generation comparison; thaumatin is a benchmark, while pH-responsive proteins remain a research track.
- [pending_review] **Human receptor functional gate**: The working target is human TAS1R2/TAS1R3. Candidate binding or docking alone does not demonstrate receptor activation or perceived sweetness.
- [pending_review] **Regulatory precedents require official verification**: Modified monellin and brazzein have reported US GRAS precedents, but notice status, intended use, production organism, and conditions of use must be read from FDA records.

## Design hypotheses
- **Single-chain monellin (sc-monellin) can be engineered to be under 100 aa by truncation of flexible loops while retaining sweetness through stabilization of the core fold.** — Natural monellin is 95 aa as a heterodimer; single-chain variants slightly longer. Evidence of mutation S76Y and W3C+R39G increasing stability (10.1038/s41598-018-31177-z) suggests core residues can be mutated. Removing 5-10 residues from non-essential loops may reduce length without disrupting binding.
- **Brazzein can be redesigned to remove potential allergenicity by mutating surface epitopes without affecting sweetness, using AI-based protein design.** — Brazzein is stable and small (54 aa), but sequence similarity to defensins may raise allergenicity concerns. Surface residue mutations predicted by ProteinMPNN can maintain fold and binding; evidence of RFdiffusion design of minibinders (10.3390/biom15111587) supports possibility.

## Workflow plan versions
- v3 `plan_f9af6e5121fe` · monellin_redesign · materialized
- v2 `plan_372081268728` · monellin_redesign · draft
- v1 `plan_80aa2a3f054a` · monellin_redesign · draft