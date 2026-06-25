# AI甜味蛋白（<100 aa、简单、优先单链）研发与验证

开发一个长度严格小于100 aa、结构简单、尽量为单链、适合饮料应用的AI甜味蛋白。

必须检索、下载并比较：
- monellin（优先 single-chain monellin / MNEI）
- brazzein
- mabinlin
- pentadin
- curculin

记录每个候选的链组成、成熟肽长度、二硫键、结构证据、受体机制、表达与稳定性风险。
优先天然骨架定向改造，不把预测结合当作甜味或安全证据。

输出可编辑的 RFdiffusion、ProteinMPNN、结构预测、Rosetta 流程，以及表达纯化、
人源 TAS1R2/TAS1R3 功能、感官、食品基质和安全法规实验计划。


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
- **A single-chain chimera of MNEI and brazzein, under 99 aa, can be designed to retain sweetness and improve stability for acidic beverages by combining the stable brazzein core with MNEI's sweetness-enhancing loops.** — MNEI (engineered single-chain monellin) shows high sweetness and stability can be improved (Mut9). Brazzein is small, stable, and has a simple fold. A fusion or chimera could exploit brazzein's disulfide-stabilized structure to scaffold MNEI's flexible regions, reducing aggregation and increasing thermo/pH stability, while maintaining or enhancing sweet taste receptor activation.

## Workflow plan versions
- v1 `plan_436ab13250bb` · monellin_redesign · materialized