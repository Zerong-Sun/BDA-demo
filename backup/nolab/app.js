const candidates = [
  ["RBDBinder_c4361", "F2", 94, "0.6 nM", 92, "1.8 A", "High", "Validated", "Anchor"],
  ["RBDBinder_a0172", "F2", 91, "1.1 nM", 89, "2.1 A", "High", "Validated", "Order"],
  ["RBDBinder_b1923", "F5", 87, "2.4 nM", 84, "2.6 A", "Medium", "Validated", "Order"],
  ["RBDBinder_c7239", "F1", 82, "4.8 nM", 76, "3.8 A", "Low", "QC risk", "Hold"],
  ["RBDBinder_a6562", "F3", 80, "5.2 nM", 83, "2.9 A", "Medium", "Retest", "Retest"],
  ["RBDBinder_d4410", "F6", 77, "7.5 nM", 80, "2.7 A", "High", "Reserve", "Reserve"],
  ["RBDBinder_e2014", "F4", 74, "9.8 nM", 72, "3.1 A", "Medium", "Reserve", "Reserve"],
  ["RBDBinder_f1021", "F7", 71, "12 nM", 79, "2.5 A", "High", "Reserve", "Reserve"],
];

const candidateDetails = [
  {
    stability: 91,
    solubility: 88,
    md: 90,
    image: "fig/bam001.png",
    description: "This lead candidate combines a stable predicted interface, strong fold confidence, low MD drift, and BLI/SPR binding confirmation, making it the safest scaffold anchor for the next BDA loop.",
    action: "Order motif-preserving variants with scaffold diversity cap: max 6 designs per family.",
  },
  {
    stability: 88,
    solubility: 86,
    md: 86,
    image: "fig/bam001.png",
    description: "This validated F2-family candidate is a strong backup to c4361. It keeps similar interface geometry with slightly weaker predicted binding and good expression feasibility.",
    action: "Keep in the synthesis queue and use it to test whether the F2 motif is robust across nearby scaffolds.",
  },
  {
    stability: 84,
    solubility: 82,
    md: 81,
    image: "fig/bam001.png",
    description: "This F5-family candidate gives useful scaffold diversity. It is less strong than c4361 but broadens the experimental batch beyond a single family.",
    action: "Order as a diversity-positive design and compare BLI/SPR kinetics against F2-family hits.",
  },
  {
    stability: 76,
    solubility: 61,
    md: 62,
    image: "fig/bam001.png",
    description: "This candidate has a plausible interface score, but low solubility and high MD drift make it a QC risk before synthesis.",
    action: "Hold from ordering and use its failure pattern as a penalty for exposed hydrophobic area.",
  },
  {
    stability: 83,
    solubility: 78,
    md: 74,
    image: "fig/bam001.png",
    description: "This retest candidate has acceptable fold confidence but needs confirmation because its predicted Kd is close to the cutoff.",
    action: "Retest after tightening expression and hydrophobic exposure filters.",
  },
  {
    stability: 80,
    solubility: 84,
    md: 78,
    image: "fig/bam001.png",
    description: "This reserve candidate has good expression feasibility, but the interface score is weaker than the primary ordered set.",
    action: "Keep as a backup if synthesis capacity expands or a primary family fails QC.",
  },
  {
    stability: 72,
    solubility: 68,
    md: 69,
    image: "fig/bam001.png",
    description: "This reserve candidate has limited fold confidence and only moderate developability, so it is not a first-pass synthesis priority.",
    action: "Use as a negative comparison for the scoring threshold.",
  },
  {
    stability: 79,
    solubility: 81,
    md: 80,
    image: "fig/bam001.png",
    description: "This reserve candidate is developability-friendly but has weaker predicted interface geometry than the validated set.",
    action: "Keep for scaffold-diverse exploration if round two needs more non-F2 designs.",
  },
];

let selectedCandidateIndex = 0;
let candidateSearchTerm = "";
let candidateStatusFilter = "all";
let priorityOnly = false;

const statusClass = {
  "Validated": "green",
  "QC risk": "amber",
  "Retest": "amber",
  "Reserve": "",
};

const nodeTemplates = {
  rf: {
    icon: "wand-sparkles",
    title: "Backbone generation",
    body: "Sample binder backbones around the constrained RBD surface",
  },
  mpnn: {
    icon: "dna",
    title: "Sequence design",
    body: "Sequence design with scaffold diversity and interface conservation",
  },
  af3: {
    icon: "scan-search",
    title: "Fold prediction",
    body: "Evaluate complex confidence, interface pAE, clashes, and contact recovery",
  },
  openmm: {
    icon: "activity",
    title: "MD stability",
    body: "Short relaxation checks interface drift and exposed hydrophobic area",
  },
  filter: {
    icon: "filter",
    title: "BDA filters",
    body: "Rank candidates by interface score, fold confidence, solubility, aggregation, and expression risk",
  },
  lab: {
    icon: "flask-conical",
    title: "Wet-lab validation",
    body: "Queue expression, purification, BLI/SPR binding, SEC monodispersity, and thermal-shift assays",
  },
};

let selectedNodeTemplate = "rf";
let customNodeCount = 0;
let toastTimer;
let automatedRouteTarget = "";

const copilotResponses = [
  {
    keywords: ["round-two", "round two", "generate", "design", "第二轮", "生成", "设计"],
    answer: "For round two, I recommend 64 variants: 40 c4361 footprint-preserving designs and 24 scaffold-diverse designs from BLI/SPR-positive families. Keep key RBD contacts fixed, then vary surface residues to reduce exposed hydrophobic area.",
  },
  {
    keywords: ["developability", "threshold", "solubility", "aggregation", "可开发性", "阈值", "溶解性", "聚集"],
    answer: "Raise the solubility gate to 88, add an exposed-hydrophobic-area penalty before synthesis, and keep expression risk at medium or better. This should reduce SEC failures without removing BLI/SPR-positive families.",
  },
  {
    keywords: ["score", "scoring", "metric", "metrics", "评分", "指标"],
    answer: "The current score combines interface geometry, complex pLDDT, interface pAE, MD drift, solubility, aggregation risk, and expression risk. c4361 ranks first because it is experimentally confirmed and balanced across these categories.",
  },
  {
    keywords: ["model", "add", "next", "workflow", "模型", "添加", "下一步", "工作流"],
    answer: "Add OpenMM MD next if you are screening final folded complexes, or add BDA filters if you already have MD and developability readouts. For this RBD binder run, MD before final filtering gives the cleanest handoff to synthesis selection.",
  },
  {
    keywords: ["c4361", "anchor", "motif", "锚点"],
    answer: "c4361 should anchor the next loop because its epitope footprint remains stable after fold prediction and short MD checks, and BLI/SPR confirms binding. Its expression profile also makes it a practical starting point for variants.",
  },
];

const computeStatus = "Compute unavailable: SUSTech Qiming HPC cluster";
const zhText = {
  "BDA Workbench": "BDA 工作台",
  "Experiments": "实验",
  "Workflow": "工作流",
  "Candidates": "候选物",
  "Results": "结果",
  "Auto route enabled": "自动路线已启用",
  "Project experiment list": "项目实验列表",
  "BDA Experiments": "BDA 实验",
  "New experiment": "新建实验",
  "BDA intelligent copilot": "BDA 智能协作助手",
  "Starts from a natural-language task definition, decomposes the experiment, adjusts the workflow, explains candidate ranking, and converts wet-lab results into next-round design constraints.": "从自然语言任务定义出发，拆解实验、调整工作流、解释候选物排序，并把湿实验结果转化为下一轮设计约束。",
  "Converts a design brief into a traceable protein-engineering loop: target definition, generative design, structural triage, developability filters, wet-lab validation, and next-round constraints.": "将设计需求转化为可追踪的蛋白工程闭环：靶标定义、生成式设计、结构筛选、可开发性过滤、湿实验验证和下一轮约束。",
  "Plan route": "规划路线",
  "Adjust workflow": "调整工作流",
  "Interpret lab results": "解释实验结果",
  "Based on current data, which candidates should be prioritized?": "基于当前数据，应该优先推进哪些候选物？",
  "Prioritize": "优先考虑",
  ". They combine strong interface scores, good pLDDT, and lower aggregation risk.": "。它们兼具较强界面评分、较好的 pLDDT 和较低聚集风险。",
  ". They combine stable interface geometry, high fold confidence, low MD drift, and acceptable expression risk.": "。它们兼具稳定界面几何、高折叠置信度、低 MD 漂移和可接受的表达风险。",
  "Route proposal for RBD high-affinity binder": "RBD 高亲和 binder 的路线方案",
  "Ready": "就绪",
  "Task requirements": "任务要求",
  "Design RBD binders with sub-5 nM predicted affinity, strong fold confidence, expression feasibility, and low aggregation risk.": "设计预测亲和力低于 5 nM、折叠置信度高、可表达且聚集风险低的 RBD binders。",
  "Design RBD binders against the ACE2-facing epitope, then select designs with confident complex geometry, low interface drift, expression feasibility, and low aggregation risk.": "针对 ACE2 侧表位设计 RBD binders，并选择复合物几何可信、界面漂移低、可表达且聚集风险低的设计。",
  "Parse target structure and interface residues": "解析靶标结构和界面残基",
  "Define epitope, antigen structure, and assay constraints": "定义表位、抗原结构和实验约束",
  "Generate backbone candidates with RFdiffusion": "使用 RFdiffusion 生成骨架候选",
  "Sample binder backbones around the target surface": "围绕靶标表面采样 binder 骨架",
  "Sample binder backbones around the constrained RBD surface": "围绕受约束的 RBD 表面采样 binder 骨架",
  "Design sequences with ProteinMPNN diversity caps": "使用 ProteinMPNN 在多样性约束下设计序列",
  "Design sequences while preserving scaffold diversity": "在保留 scaffold 多样性的同时设计序列",
  "Sequence design with scaffold diversity and interface conservation": "兼顾 scaffold 多样性和界面保守性的序列设计",
  "Fold complexes with AlphaFold3": "使用 AlphaFold3 预测复合物结构",
  "Screen complex confidence, interface pAE, and clashes": "筛选复合物置信度、界面 pAE 和空间冲突",
  "Evaluate complex confidence, interface pAE, clashes, and contact recovery": "评估复合物置信度、界面 pAE、空间冲突和接触恢复",
  "Run OpenMM MD stability checks": "运行 OpenMM MD 稳定性检查",
  "Run short MD checks for interface drift and buried exposure": "运行短程 MD 检查界面漂移和埋藏暴露",
  "Short relaxation checks interface drift and exposed hydrophobic area": "短程 relaxation 检查界面漂移和暴露疏水面积",
  "Select wet-lab queue with BDA filters": "使用 BDA filters 选择湿实验队列",
  "Select expression-ready candidates for BLI/SPR and SEC": "选择可表达候选物进入 BLI/SPR 和 SEC",
  "Estimated output": "预计输出",
  "ordered candidates with score table, structures, FASTA, and filtering reasons.": "个订购候选物，包含评分表、结构、FASTA 和筛选原因。",
  "ordered candidates with FASTA, complex structures, score provenance, and assay-ready selection reasons.": "个订购候选物，包含 FASTA、复合物结构、评分来源和面向实验的选择原因。",
  "Open workflow": "打开工作流",
  "Constraint editor and node updates": "约束编辑器和节点更新",
  "Review": "待审阅",
  "Developability threshold": "可开发性阈值",
  "Solubility": "溶解性",
  "Hydrophobic patch penalty": "疏水斑块惩罚",
  "Expression risk gate": "表达风险门控",
  "Workflow changes": "工作流变更",
  "Add expression-risk filtering before ordering": "订购前加入表达风险筛选",
  "Gate candidates by expression risk before synthesis": "合成前按表达风险设置门控",
  "Move MD stability before final BDA filters": "将 MD 稳定性检查移到最终 BDA filters 之前",
  "Move MD drift checks before final developability filters": "将 MD 漂移检查移到最终可开发性过滤之前",
  "Cap each scaffold family at 6 ordered variants": "每个 scaffold 家族最多订购 6 个变体",
  "Send SEC failures into round-two penalties": "将 SEC 失败反馈为第二轮惩罚项",
  "Convert SEC aggregation failures into round-two penalties": "将 SEC 聚集失败转化为第二轮惩罚项",
  "Copilot recommendation": "Copilot 建议",
  "Keep c4361 as the motif anchor, then trade a small amount of predicted affinity for lower aggregation and stronger expression reliability.": "保留 c4361 作为 motif 锚点，用少量预测亲和力换取更低聚集和更可靠表达。",
  "Keep the c4361 interface motif as the anchor, but relax pure affinity ranking when a design shows high hydrophobic exposure or weak expression confidence.": "保留 c4361 界面 motif 作为锚点，但当设计显示高疏水暴露或表达置信度弱时，放松纯亲和力排序。",
  "Apply to workflow": "应用到工作流",
  "Evidence summary and next-round constraints": "证据总结和下一轮约束",
  "Closed loop": "闭环完成",
  "Hit rate": "命中率",
  "Validated binders cluster around F2 and F5 families.": "验证命中的 binders 主要集中在 F2 和 F5 家族。",
  "BLI/SPR positives cluster around F2 and F5 families.": "BLI/SPR 阳性候选物主要集中在 F2 和 F5 家族。",
  "Best Kd": "最佳 Kd",
  "RBDBinder_c4361 should anchor motif-preserving variants.": "RBDBinder_c4361 应作为保留 motif 变体的锚点。",
  "Measured on the top BLI/SPR-confirmed clone.": "来自 BLI/SPR 确认的 Top 克隆实测结果。",
  "Main loss": "主要损失",
  "Hydrophobic patch exposure explains most aggregation failures.": "疏水斑块暴露解释了大多数聚集失败。",
  "SEC aggregation, not binding loss, explains most QC attrition.": "大多数 QC 损失来自 SEC 聚集，而不是结合信号丢失。",
  "Next round constraints": "下一轮约束",
  "Preserve c4361 binding motif and interface geometry": "保留 c4361 结合 motif 和界面几何",
  "Preserve c4361 interface contacts and epitope footprint": "保留 c4361 界面接触和表位 footprint",
  "Raise solubility threshold before wet-lab queue selection": "湿实验队列选择前提高溶解性阈值",
  "Penalize exposed hydrophobic patches before ordering": "订购前惩罚暴露疏水斑块",
  "Increase scaffold diversity across validated families": "在已验证家族中提高 scaffold 多样性",
  "Increase scaffold diversity across BLI/SPR-positive families": "在 BLI/SPR 阳性家族中提高 scaffold 多样性",
  "Open results": "打开结果",
  "Active project": "活跃项目",
  "Project_test_0423 is running": "Project_test_0423 正在运行",
  "Wet-lab hits": "湿实验命中",
  "Binding positives": "结合阳性",
  "Validated RBD binder candidates": "已验证 RBD binder 候选物",
  "BLI/SPR-positive candidates": "BLI/SPR 阳性候选物",
  "Qiming HPC resources unavailable": "启明超算资源不可用",
  "Preserve c4361 motif and diversify scaffolds": "保留 c4361 motif 并提高 scaffold 多样性",
  "Running": "运行中",
  "Draft": "草稿",
  "Queued": "排队中",
  "SARS-CoV-2 RBD binder design. Generate candidate sequences, select expression-ready designs, validate hits, and feed wet-lab data into the second design round.": "SARS-CoV-2 RBD binder 设计。生成候选序列，选择可表达设计，验证命中，并将湿实验数据反馈到第二轮设计。",
  "SARS-CoV-2 RBD binder design. Generate RBD-facing binders, triage complex confidence and developability, validate expression and BLI/SPR binding, then feed SEC and affinity results into round two.": "SARS-CoV-2 RBD binder 设计。生成面向 RBD 的 binders，筛选复合物置信度和可开发性，验证表达与 BLI/SPR 结合，再将 SEC 和亲和力结果反馈到第二轮。",
  "Route": "路线",
  "Stage": "阶段",
  "Validation feedback": "验证反馈",
  "Open": "打开",
  "Programmable protein-cage cargo display. The task definition is complete, and route planning is waiting for target constraints and assay conditions.": "可编程蛋白笼货物展示。任务定义已完成，路线规划等待靶标约束和实验条件。",
  "Auto route pending": "自动路线待生成",
  "Task definition": "任务定义",
  "Improve activity and solubility on a fragile enzyme scaffold, using expression and thermal-shift data to constrain mutation proposals.": "在脆弱酶 scaffold 上提升活性和溶解性，并用表达与热转移数据约束突变建议。",
  "Sequence optimization": "序列优化",
  "Input review": "输入审阅",
  "Add node": "添加节点",
  "Start workflow": "启动工作流",
  "Add workflow card": "添加工作流卡片",
  "Choose a model or method": "选择模型或方法",
  "Model cards": "模型卡片",
  "Backbone generation": "骨架生成",
  "Sequence design": "序列设计",
  "Fold prediction": "折叠预测",
  "Stability simulation": "稳定性模拟",
  "Selection layer": "筛选层",
  "Wet-lab validation": "湿实验验证",
  "Experiment queue": "实验队列",
  "Method controls": "方法控制",
  "Affinity score": "亲和力评分",
  "Diversity cap": "多样性上限",
  "Expression risk": "表达风险",
  "Aggregation penalty": "聚集惩罚",
  "Auto report": "自动报告",
  "Compute access": "计算节点接入",
  "SUSTech Qiming HPC cluster": "南科大启明超算集群",
  "All resources unavailable": "所有资源均不可用",
  "Unavailable": "不可用",
  "Preview card": "预览卡片",
  "Explore binder geometry with RFdiffusion": "使用 RFdiffusion 探索 binder 几何结构",
  "Affinity score, Diversity cap, Auto report": "亲和力评分、多样性上限、自动报告",
  "Add card to workflow": "添加卡片到工作流",
  "Target protein": "靶标蛋白",
  "RBD structure, interface residues, assay constraints": "RBD 结构、界面残基、实验约束",
  "RBD structure, ACE2-facing epitope, BLI/SPR and SEC constraints": "RBD 结构、ACE2 侧表位、BLI/SPR 和 SEC 约束",
  "3/3 inputs confirmed": "3/3 输入已确认",
  "1,248/18,000 generated": "已生成 1,248/18,000",
  "ProteinMPNN sequence search with diversity constraints": "带多样性约束的 ProteinMPNN 序列搜索",
  "384/1,248 designed": "已设计 384/1,248",
  "AlphaFold3 evaluates complex structure and local confidence": "AlphaFold3 评估复合物结构和局部置信度",
  "312/384 folded": "已折叠 312/384",
  "MD stability": "MD 稳定性",
  "OpenMM MD checks conformational drift and interface stability": "OpenMM MD 检查构象漂移和界面稳定性",
  "120/312 simulated": "已模拟 120/312",
  "Affinity, solubility, aggregation risk, expression risk": "亲和力、溶解性、聚集风险、表达风险",
  "Interface score, fold confidence, solubility, aggregation, expression risk": "界面评分、折叠置信度、溶解性、聚集和表达风险",
  "Rank candidates by interface score, fold confidence, solubility, aggregation, and expression risk": "按界面评分、折叠置信度、溶解性、聚集和表达风险对候选物排序",
  "96/384 passed filters": "96/384 通过筛选",
  "Expression, purification, BLI/SPR, SEC, thermal shift": "表达、纯化、BLI/SPR、SEC、热转移",
  "Expression, purification, BLI/SPR binding, SEC monodispersity, thermal shift": "表达、纯化、BLI/SPR 结合、SEC 单分散性、热转移",
  "Queue expression, purification, BLI/SPR binding, SEC monodispersity, and thermal-shift assays": "排队进行表达、纯化、BLI/SPR 结合、SEC 单分散性和热转移实验",
  "9/48 hits confirmed": "9/48 命中确认",
  "Design high-affinity RBD binders with expression and developability constraints": "设计带表达和可开发性约束的高亲和 RBD binders",
  "Design RBD binders for ACE2-facing epitope with expression and developability constraints": "针对 ACE2 侧表位设计带表达和可开发性约束的 RBD binders",
  "5/5 constraints parsed": "5/5 约束已解析",
  "Based on current scores, which candidates should enter the experimental queue?": "基于当前评分，哪些候选物应该进入实验队列？",
  ". They are better balanced across interface score, predicted Kd, pLDDT, and expression risk.": "。它们在界面评分、预测 Kd、pLDDT 和表达风险之间更均衡。",
  ". They balance interface geometry, complex confidence, MD drift, and expression risk.": "。它们在界面几何、复合物置信度、MD 漂移和表达风险之间更均衡。",
  "Can you propose a set of alternatives with stronger developability?": "能否提出一组可开发性更强的替代方案？",
  "Workflow adjusted: developability penalty added": "工作流已调整：加入可开发性惩罚",
  "Yes. For round two, raise the solubility threshold, reduce hydrophobic patch exposure, and add expression-risk filtering before ordering. This may trade off some predicted affinity, but should reduce SEC aggregation failures.": "可以。第二轮提高溶解性阈值，降低疏水斑块暴露，并在订购前加入表达风险筛选。这可能牺牲少量预测亲和力，但应能减少 SEC 聚集失败。",
  "Yes. For round two, penalize exposed hydrophobic area, keep expression-risk filtering before synthesis, and preserve the validated c4361 interface contacts. This should reduce SEC aggregation failures without losing the binding footprint.": "可以。第二轮惩罚暴露疏水面积，合成前保留表达风险筛选，并保留已验证的 c4361 界面接触。这应能减少 SEC 聚集失败，同时不丢失结合 footprint。",
  "Keep the c4361 binding motif, but increase scaffold diversity in round two.": "保留 c4361 结合 motif，但在第二轮提高 scaffold 多样性。",
  "Noted. In the next round I will preserve the key c4361 binding motif while limiting how many designs can come from a single family, so the experimental batch is not dominated by one scaffold.": "已记录。下一轮我会保留关键的 c4361 结合 motif，同时限制单一家族的设计数量，避免实验批次被一个 scaffold 主导。",
  "Generate round-two designs": "生成第二轮设计",
  "Adjust developability threshold": "调整可开发性阈值",
  "Explain scoring metrics": "解释评分指标",
  "Which model should I add next?": "下一步应该添加哪个模型？",
  "BDA selection layer": "BDA 筛选层",
  "Candidate table": "候选物表",
  "Export CSV": "导出 CSV",
  "Search candidate or family": "搜索候选物或家族",
  "All": "全部",
  "Priority only": "仅优先项",
  "No candidates match current filters": "没有候选物符合当前筛选",
  "Compute node status": "计算节点状态",
  "GPU unavailable": "GPU 不可用",
  "CPU unavailable": "CPU 不可用",
  "Generated": "已生成",
  "Backbones explored": "已探索骨架",
  "Designed": "已设计",
  "Sequences sampled": "已采样序列",
  "Folded": "已折叠",
  "Complexes scored": "复合物已评分",
  "Simulated": "已模拟",
  "MD checks completed": "MD 检查完成",
  "Ordered": "已订购",
  "Wet-lab queue": "湿实验队列",
  "Candidate": "候选物",
  "Family": "家族",
  "Affinity": "亲和力",
  "Interface": "界面",
  "Pred Kd": "预测 Kd",
  "MD drift": "MD 漂移",
  "Expression": "表达",
  "Status": "状态",
  "Decision": "决策",
  "High": "高",
  "Medium": "中",
  "Low": "低",
  "Validated": "已验证",
  "QC risk": "QC 风险",
  "Retest": "复测",
  "Reserve": "备用",
  "Hold": "暂缓",
  "Anchor": "锚点",
  "Order": "订购",
  "Selection rules": "筛选规则",
  "Predicted Kd below 5 nM or strong interface rescue potential": "预测 Kd 低于 5 nM，或有较强界面挽救潜力",
  "Top-decile interface score with no severe clash at the epitope": "界面评分位于前 10%，且表位处无严重空间冲突",
  "Complex pLDDT above 82 with no broken interface loop": "复合物 pLDDT 高于 82，且界面 loop 不破裂",
  "Complex pLDDT above 82 and acceptable interface pAE": "复合物 pLDDT 高于 82，且界面 pAE 可接受",
  "MD drift below 3.2 A across the interface region": "界面区域 MD 漂移低于 3.2 A",
  "MD interface drift below 3.2 A after short relaxation": "短程 relaxation 后界面 MD 漂移低于 3.2 A",
  "Expression risk marked medium or better before ordering": "订购前表达风险至少为中等或更好",
  "Expression risk medium or better before synthesis": "合成前表达风险为中等或更好",
  "AI Beagle Copilot note": "AI Beagle Copilot 注释",
  "c4361 remains the anchor because its binding motif survives fold prediction and MD checks. Round two should preserve that motif while forcing more family diversity and lower hydrophobic patch exposure.": "c4361 仍是锚点，因为其结合 motif 通过了折叠预测和 MD 检查。第二轮应保留该 motif，同时强制更高家族多样性并降低疏水斑块暴露。",
  "c4361 remains the anchor because its interface contacts survive fold prediction, short MD checks, and BLI/SPR confirmation. Round two should preserve the epitope footprint while increasing scaffold diversity and lowering exposed hydrophobic area.": "c4361 仍是锚点，因为其界面接触通过了折叠预测、短程 MD 检查和 BLI/SPR 确认。第二轮应保留表位 footprint，同时提高 scaffold 多样性并降低暴露疏水面积。",
  "This lead candidate balances predicted affinity, fold confidence, low MD drift, and expression feasibility, making it the safest anchor scaffold for the next BDA loop.": "该领先候选物在预测亲和力、折叠置信度、低 MD 漂移和表达可行性之间取得平衡，是下一轮 BDA 循环最稳妥的锚点 scaffold。",
  "This lead candidate combines a stable predicted interface, strong fold confidence, low MD drift, and BLI/SPR binding confirmation, making it the safest scaffold anchor for the next BDA loop.": "该领先候选物兼具稳定预测界面、强折叠置信度、低 MD 漂移和 BLI/SPR 结合确认，是下一轮 BDA 循环最稳妥的 scaffold 锚点。",
  "Stability": "稳定性",
  "MD stability": "MD 稳定性",
  "Next action": "下一步行动",
  "Order motif-preserving variants with scaffold diversity cap: max 6 designs per family.": "订购保留 motif 的变体，并限制 scaffold 多样性：每个家族最多 6 个设计。",
  "Closed-loop evidence": "闭环证据",
  "Results and delivery": "结果与交付",
  "Prepare package": "准备交付包",
  "9/48 candidates validated": "9/48 候选物已验证",
  "9/48 BLI/SPR-positive candidates": "9/48 个 BLI/SPR 阳性候选物",
  "Main failure": "主要失败原因",
  "Main QC loss": "主要 QC 损失",
  "Aggregation explains most QC loss": "聚集解释了大多数 QC 损失",
  "Aggregation explains most post-binding loss": "聚集解释了大多数结合后的损失",
  "Round 2": "第二轮",
  "Preserve motif and penalize hydrophobic patches": "保留 motif 并惩罚疏水斑块",
  "Preserve epitope footprint and penalize hydrophobic exposure": "保留表位 footprint 并惩罚疏水暴露",
  "Interpretation": "解读",
  "BDA validated this route: AI-generated binders produced measurable wet-lab hits, but stronger developability constraints are needed before client-facing IND-oriented work.": "BDA 验证了这条路线：AI 生成的 binders 产生了可测量的湿实验命中，但在面向客户的 IND 导向工作前，需要更强的可开发性约束。",
  "The route produced measurable BLI/SPR binding from AI-designed candidates. The main improvement is not more affinity pressure, but stronger developability control before synthesis: hydrophobic exposure, expression risk, and SEC monodispersity.": "这条路线从 AI 设计候选物中产生了可测量的 BLI/SPR 结合。主要改进不是进一步提高亲和力压力，而是在合成前加强可开发性控制：疏水暴露、表达风险和 SEC 单分散性。",
  "Delivery package": "交付包",
  "Executive summary and route rationale": "执行摘要和路线依据",
  "FASTA and score table for 48 sequences": "48 条序列的 FASTA 和评分表",
  "High-priority structures and experimental readouts": "高优先级结构和实验读数",
  "Round-two model update brief": "第二轮模型更新简报",
  "Validation readouts": "验证读数",
  "Step": "步骤",
  "Pass": "通过",
  "Signal": "信号",
  "Implication": "含义",
  "Expression screen": "表达筛选",
  "Strong expression for F2/F5 families": "F2/F5 家族表达强",
  "F2/F5 families express reliably": "F2/F5 家族表达可靠",
  "Keep family cap, not family removal": "保留家族上限，不移除家族",
  "Keep family cap; do not remove validated families": "保留家族上限，不移除已验证家族",
  "Purification": "纯化",
  "Low-yield failures clustered in F1": "低产量失败集中在 F1",
  "Low-yield failures cluster in F1": "低产量失败集中在 F1",
  "Add expression-risk penalty earlier": "更早加入表达风险惩罚",
  "Add expression-risk penalty before synthesis": "合成前加入表达风险惩罚",
  "BLI / SPR": "BLI / SPR",
  "Best measured Kd: 0.6 nM": "最佳实测 Kd：0.6 nM",
  "Preserve c4361 motif in round two": "第二轮保留 c4361 motif",
  "Preserve c4361 epitope footprint in round two": "第二轮保留 c4361 表位 footprint",
  "SEC / aggregation": "SEC / 聚集",
  "Hydrophobic patches explain most QC loss": "疏水斑块解释了大多数 QC 损失",
  "Exposed hydrophobic patches explain most QC loss": "暴露疏水斑块解释了大多数 QC 损失",
  "Raise developability threshold": "提高可开发性阈值",
  "Penalize hydrophobic exposure before ordering": "订购前惩罚疏水暴露",
  "Round-two design brief": "第二轮设计简报",
  "Preserve c4361 interface motif and hydrogen-bond geometry": "保留 c4361 界面 motif 和氢键几何",
  "Preserve c4361 epitope footprint and key polar contacts": "保留 c4361 表位 footprint 和关键极性接触",
  "Increase scaffold diversity across F2, F5, and reserve families": "提高 F2、F5 和备用家族中的 scaffold 多样性",
  "Increase scaffold diversity across BLI/SPR-positive families": "提高 BLI/SPR 阳性家族中的 scaffold 多样性",
  "Reduce hydrophobic patch exposure before MD selection": "MD 选择前降低疏水斑块暴露",
  "Reduce exposed hydrophobic area before synthesis": "合成前降低暴露疏水面积",
  "Order 64 variants: 40 exploitation, 24 exploration": "订购 64 个变体：40 个开发型，24 个探索型",
  "Order 64 variants: 40 motif-preserving, 24 scaffold-diverse": "订购 64 个变体：40 个保留 motif，24 个 scaffold 多样化",
  "Client package": "客户交付包",
  "Route rationale and model configuration summary": "路线依据和模型配置摘要",
  "Full candidate score table with filtering reasons": "完整候选物评分表和筛选原因",
  "Top structures, FASTA, and wet-lab readout bundle": "Top 结构、FASTA 和湿实验读数包",
  "Round-two constraints ready for workflow rerun": "可用于工作流重跑的第二轮约束",
  "Compute unavailable: SUSTech Qiming HPC cluster": "计算不可用：南科大启明超算集群",
  "No method selected": "未选择方法",
  "Candidate detail updated": "候选物详情已更新",
  "Filtered candidate view updated": "候选物视图已更新",
  "Candidate CSV export prepared": "候选物 CSV 导出已准备",
  "Delivery package queued": "交付包已加入队列",
  "Node builder opened": "节点添加面板已打开",
  "Workflow card added": "工作流卡片已添加",
  "Workflow run started": "工作流已启动",
  "New route panel opened": "新建路线面板已打开",
  "Auto route drafted": "自动路线草稿已生成",
  "Checking compute node status": "正在确认计算节点状态",
  "Compute nodes unavailable": "计算节点不可用",
  "New route": "新建路线",
  "New automated route": "新建自动路线",
  "Define target protein": "定义靶标蛋白",
  "Target protein": "靶标蛋白",
  "SARS-CoV-2 Spike RBD (PDB 6M0J), ACE2-facing epitope": "SARS-CoV-2 Spike RBD（PDB 6M0J），ACE2 侧表位",
  "Example constraint": "示例约束",
  "Design binders for the ACE2-facing epitope; prioritize complex confidence, interface pAE, expression feasibility, and SEC monodispersity before synthesis.": "针对 ACE2 侧表位设计 binders；合成前优先考虑复合物置信度、界面 pAE、表达可行性和 SEC 单分散性。",
  "Auto route": "自动规划路线",
  "Blank automated workflow": "空白自动化流程",
  "Target protein parsed. Add model cards or run compute check to continue.": "靶标蛋白已解析。添加模型卡片或运行计算检查以继续。",
  "Compute status pending": "计算状态待确认",
  "Compute check failed: all Qiming HPC resources unavailable": "计算检查失败：启明超算资源均不可用",
  "Upload protein template": "上传蛋白质模板",
  "No template selected": "未选择模板",
  "Protein template uploaded": "蛋白质模板已上传",
  "Export data": "导出数据",
  "Results data exported": "结果数据已导出",
  "This validated F2-family candidate is a strong backup to c4361. It keeps similar interface geometry with slightly weaker predicted binding and good expression feasibility.": "这个已验证的 F2 家族候选物是 c4361 的强备选。它保留了相似界面几何，预测结合略弱，但表达可行性较好。",
  "Keep in the synthesis queue and use it to test whether the F2 motif is robust across nearby scaffolds.": "保留在合成队列中，用于测试 F2 motif 在相近 scaffold 中是否稳健。",
  "This F5-family candidate gives useful scaffold diversity. It is less strong than c4361 but broadens the experimental batch beyond a single family.": "这个 F5 家族候选物提供有价值的 scaffold 多样性。它弱于 c4361，但能避免实验批次局限于单一家族。",
  "Order as a diversity-positive design and compare BLI/SPR kinetics against F2-family hits.": "作为多样性正向设计订购，并将其 BLI/SPR 动力学与 F2 家族命中物比较。",
  "This candidate has a plausible interface score, but low solubility and high MD drift make it a QC risk before synthesis.": "该候选物界面评分尚可，但低溶解性和高 MD 漂移使其在合成前就具有 QC 风险。",
  "Hold from ordering and use its failure pattern as a penalty for exposed hydrophobic area.": "暂缓订购，并将其失败模式作为暴露疏水面积的惩罚依据。",
  "This retest candidate has acceptable fold confidence but needs confirmation because its predicted Kd is close to the cutoff.": "该复测候选物折叠置信度可接受，但预测 Kd 接近阈值，因此需要确认。",
  "Retest after tightening expression and hydrophobic exposure filters.": "收紧表达和疏水暴露过滤后再复测。",
  "This reserve candidate has good expression feasibility, but the interface score is weaker than the primary ordered set.": "该备用候选物表达可行性较好，但界面评分弱于首批订购集合。",
  "Keep as a backup if synthesis capacity expands or a primary family fails QC.": "若合成容量扩大或主力家族 QC 失败，可作为备用。",
  "This reserve candidate has limited fold confidence and only moderate developability, so it is not a first-pass synthesis priority.": "该备用候选物折叠置信度有限，可开发性中等，因此不是首轮合成优先项。",
  "Use as a negative comparison for the scoring threshold.": "作为评分阈值的负向对照使用。",
  "This reserve candidate is developability-friendly but has weaker predicted interface geometry than the validated set.": "该备用候选物可开发性较友好，但预测界面几何弱于已验证集合。",
  "Keep for scaffold-diverse exploration if round two needs more non-F2 designs.": "如果第二轮需要更多非 F2 设计，可保留用于 scaffold 多样化探索。",
  "Explain why c4361 should anchor round two": "解释为什么 c4361 应作为第二轮锚点",
  "For round two, I recommend 64 variants: 40 motif-preserving c4361 derivatives and 24 exploration designs from F5/F6 scaffolds. Keep the RBD contact motif fixed, then vary surface residues to reduce aggregation.": "第二轮我建议 64 个变体：40 个保留 c4361 motif 的衍生设计，以及 24 个来自 F5/F6 scaffold 的探索设计。固定 RBD 接触 motif，再改变表面残基以降低聚集。",
  "For round two, I recommend 64 variants: 40 c4361 footprint-preserving designs and 24 scaffold-diverse designs from BLI/SPR-positive families. Keep key RBD contacts fixed, then vary surface residues to reduce exposed hydrophobic area.": "第二轮我建议 64 个变体：40 个保留 c4361 footprint 的设计，以及 24 个来自 BLI/SPR 阳性家族的 scaffold 多样化设计。固定关键 RBD 接触，再改变表面残基以降低暴露疏水面积。",
  "Raise the solubility gate to 88, add a hydrophobic patch penalty before ordering, and keep expression risk at medium or better. This should reduce SEC failures without removing the strongest affinity families.": "将溶解性门槛提高到 88，订购前加入疏水斑块惩罚，并保持表达风险为中等或更好。这应能减少 SEC 失败，同时不移除亲和力最强的家族。",
  "Raise the solubility gate to 88, add an exposed-hydrophobic-area penalty before synthesis, and keep expression risk at medium or better. This should reduce SEC failures without removing BLI/SPR-positive families.": "将溶解性门槛提高到 88，合成前加入暴露疏水面积惩罚，并保持表达风险为中等或更好。这应能减少 SEC 失败，同时不移除 BLI/SPR 阳性家族。",
  "The current score combines predicted affinity, complex pLDDT, MD drift, solubility, aggregation risk, and expression risk. c4361 ranks first because it is strong across all categories, not just affinity.": "当前评分综合预测亲和力、复合物 pLDDT、MD 漂移、溶解性、聚集风险和表达风险。c4361 排名第一，因为它不是只在亲和力上强，而是在所有类别上都比较均衡。",
  "The current score combines interface geometry, complex pLDDT, interface pAE, MD drift, solubility, aggregation risk, and expression risk. c4361 ranks first because it is experimentally confirmed and balanced across these categories.": "当前评分综合界面几何、复合物 pLDDT、界面 pAE、MD 漂移、溶解性、聚集风险和表达风险。c4361 排名第一，因为它已有实验确认，并且在这些维度上较均衡。",
  "Add OpenMM MD next if you are screening final candidates, or add BDA filters if you already have fold predictions. For this RBD binder run, MD before BDA filters gives the cleanest handoff to wet-lab selection.": "如果正在筛最终候选物，下一步添加 OpenMM MD；如果已经有折叠预测，则添加 BDA filters。对这次 RBD binder 任务来说，在 BDA filters 前做 MD 能最清晰地交接到湿实验选择。",
  "Add OpenMM MD next if you are screening final folded complexes, or add BDA filters if you already have MD and developability readouts. For this RBD binder run, MD before final filtering gives the cleanest handoff to synthesis selection.": "如果正在筛最终折叠复合物，下一步添加 OpenMM MD；如果已经有 MD 和可开发性读数，则添加 BDA filters。对这次 RBD binder 任务来说，在最终筛选前做 MD 能最清晰地交接到合成选择。",
  "c4361 should anchor the next loop because its interface motif remains stable after fold prediction and MD checks, while its measured Kd and expression profile make it a practical starting point for variants.": "c4361 应作为下一轮锚点，因为它的界面 motif 在折叠预测和 MD 检查后仍保持稳定，同时实测 Kd 和表达表现也让它适合作为变体设计起点。",
  "c4361 should anchor the next loop because its epitope footprint remains stable after fold prediction and short MD checks, and BLI/SPR confirms binding. Its expression profile also makes it a practical starting point for variants.": "c4361 应作为下一轮锚点，因为它的表位 footprint 在折叠预测和短程 MD 检查后仍保持稳定，并且 BLI/SPR 确认了结合。它的表达表现也适合作为变体设计起点。",
  "I would first check whether the requested change affects affinity, fold confidence, MD drift, expression risk, or wet-lab throughput. For this workflow, the safest next step is to preserve the c4361 motif, add developability penalties, and keep a diverse 48-64 candidate queue.": "我会先检查这个变更是否影响亲和力、折叠置信度、MD 漂移、表达风险或湿实验通量。对这个工作流来说，最稳妥的下一步是保留 c4361 motif，加入可开发性惩罚，并保持 48-64 个多样化候选队列。",
};
let currentLanguage = localStorage.getItem("bda-language") || "en";

function showToast(message) {
  const toast = document.querySelector("#toast");
  if (!toast) return;
  toast.textContent = translateText(message);
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 1800);
}

function setRoute(route) {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  document.querySelector(`#view-${route}`)?.classList.add("active");

  document.querySelectorAll("[data-route]").forEach((el) => {
    el.classList.toggle("active", el.dataset.route === route && el.tagName === "A");
  });

  window.location.hash = route;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function translateText(text) {
  return currentLanguage === "zh" ? (zhText[text] || text) : text;
}

function applyLanguage() {
  document.documentElement.lang = currentLanguage === "zh" ? "zh-CN" : "en";

  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent || ["SCRIPT", "STYLE"].includes(parent.tagName) || parent.closest("#languageToggle")) return NodeFilter.FILTER_REJECT;
      return node.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    },
  });

  while (walker.nextNode()) {
    const node = walker.currentNode;
    const original = node.__bdaOriginalText || node.nodeValue.trim();
    node.__bdaOriginalText = original;
    const leading = node.nodeValue.match(/^\s*/)[0];
    const trailing = node.nodeValue.match(/\s*$/)[0];
    node.nodeValue = `${leading}${translateText(original)}${trailing}`;
  }

  document.querySelectorAll("[data-i18n-en]").forEach((item) => {
    item.textContent = currentLanguage === "zh" ? item.dataset.i18nZh : item.dataset.i18nEn;
  });

  const input = document.querySelector("#copilotInput");
  if (input) {
    input.dataset.i18nValue = input.dataset.i18nValue || input.value;
    input.value = currentLanguage === "zh" ? (zhText[input.dataset.i18nValue] || input.dataset.i18nValue) : input.dataset.i18nValue;
  }

  const candidateSearch = document.querySelector("#candidateSearch");
  if (candidateSearch) candidateSearch.placeholder = translateText("Search candidate or family");

  document.querySelector("#languageToggle").textContent = currentLanguage === "zh" ? "EN" : "中文";
}

function filteredCandidateEntries() {
  const normalizedSearch = candidateSearchTerm.trim().toLowerCase();
  const priorityDecisions = new Set(["Anchor", "Order", "Retest"]);

  return candidates
    .map((candidate, index) => ({ candidate, index }))
    .filter(({ candidate }) => {
      const [name, family, , , , , , status, decision] = candidate;
      const matchesSearch = !normalizedSearch || `${name} ${family}`.toLowerCase().includes(normalizedSearch);
      const matchesStatus = candidateStatusFilter === "all" || status === candidateStatusFilter;
      const matchesPriority = !priorityOnly || status === "Validated" || priorityDecisions.has(decision);
      return matchesSearch && matchesStatus && matchesPriority;
    });
}

function renderCandidates() {
  const body = document.querySelector("#candidateRows");
  const entries = filteredCandidateEntries();

  if (!entries.length) {
    body.innerHTML = `
      <tr class="empty-row">
        <td colspan="9">No candidates match current filters</td>
      </tr>
    `;
    applyLanguage();
    return;
  }

  body.innerHTML = entries.map(({ candidate, index }) => {
    const [name, family, affinity, kd, plddt, mdDrift, expression, status, decision] = candidate;
    const pillClass = statusClass[status] || "";
    return `
      <tr data-candidate-index="${index}" tabindex="0" class="${index === selectedCandidateIndex ? "selected-row" : ""}">
        <td><strong>${name}</strong></td>
        <td>${family}</td>
        <td>${affinity}</td>
        <td>${kd}</td>
        <td>${plddt}</td>
        <td>${mdDrift}</td>
        <td>${expression}</td>
        <td><span class="pill ${pillClass}">${status}</span></td>
        <td>${decision}</td>
      </tr>
    `;
  }).join("");
  bindCandidateRows();
}

function applyCandidateFilters(notify = false) {
  const entries = filteredCandidateEntries();
  if (entries.length && !entries.some((entry) => entry.index === selectedCandidateIndex)) {
    selectedCandidateIndex = entries[0].index;
  }
  renderCandidates();
  if (entries.length) updateCandidateDetail(selectedCandidateIndex);
  if (notify) showToast("Filtered candidate view updated");
}

function updateCandidateDetail(index, notify = false) {
  selectedCandidateIndex = index;
  const [name, , interfaceScore, , plddt] = candidates[index];
  const detail = candidateDetails[index];
  document.querySelector("#candidateImage").src = detail.image;
  document.querySelector("#candidateTitle").textContent = name;
  document.querySelector("#candidateDescription").textContent = detail.description;
  document.querySelector("#candidateInterface").textContent = interfaceScore;
  document.querySelector("#candidateInterfaceBar").value = interfaceScore;
  document.querySelector("#candidateStability").textContent = plddt;
  document.querySelector("#candidateStabilityBar").value = plddt;
  document.querySelector("#candidateSolubility").textContent = detail.solubility;
  document.querySelector("#candidateSolubilityBar").value = detail.solubility;
  document.querySelector("#candidateMd").textContent = detail.md;
  document.querySelector("#candidateMdBar").value = detail.md;
  document.querySelector("#candidateAction").textContent = detail.action;
  document.querySelectorAll("[data-candidate-index]").forEach((row) => {
    row.classList.toggle("selected-row", Number(row.dataset.candidateIndex) === index);
  });
  applyLanguage();
  if (notify) showToast("Candidate detail updated");
}

function bindCandidateRows() {
  document.querySelectorAll("[data-candidate-index]").forEach((row) => {
    row.addEventListener("click", () => updateCandidateDetail(Number(row.dataset.candidateIndex), true));
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        updateCandidateDetail(Number(row.dataset.candidateIndex), true);
      }
    });
  });
}

function selectedMethods() {
  const methods = Array.from(document.querySelectorAll("[data-method]:checked")).map((item) => item.dataset.method);
  return methods.length ? methods : ["No method selected"];
}

function renderNodePreview() {
  const preview = document.querySelector("#nodePreview");
  if (!preview) return;
  const template = nodeTemplates[selectedNodeTemplate];
  preview.innerHTML = `
    <header><i data-lucide="${template.icon}"></i><span>${template.title}</span></header>
    <p>${template.body}</p>
    <footer><span class="node-port"></span>${selectedMethods().join(", ")}</footer>
    <footer><i data-lucide="server-off"></i>${computeStatus}</footer>
  `;
  if (window.lucide) window.lucide.createIcons();
  applyLanguage();
}

function addCustomNode() {
  const layer = document.querySelector("#customNodeLayer");
  if (!layer) return;
  const template = nodeTemplates[selectedNodeTemplate];
  const methods = selectedMethods().join(", ");
  const positions = [
    { left: 285, top: 70 },
    { left: 515, top: 70 },
    { left: 285, top: 470 },
    { left: 48, top: 250 },
  ];
  const position = positions[customNodeCount % positions.length];
  customNodeCount += 1;
  document.querySelector(".map-panel")?.classList.add("has-custom");

  const node = document.createElement("article");
  node.className = "node custom-node";
  node.style.left = `${position.left}px`;
  node.style.top = `${position.top}px`;
  node.innerHTML = `
    <header><i data-lucide="${template.icon}"></i><span>${template.title}</span></header>
    <p>${template.body}</p>
    <footer><span class="node-port"></span>${methods}</footer>
    <footer><i data-lucide="server-off"></i>${computeStatus}</footer>
  `;
  layer.appendChild(node);
  if (window.lucide) window.lucide.createIcons();
  applyLanguage();
  showToast("Workflow card added");
}

function draftAutoRoute() {
  const targetInput = document.querySelector("#targetProteinInput");
  const target = targetInput?.value.trim() || "SARS-CoV-2 Spike RBD (PDB 6M0J), ACE2-facing epitope";
  automatedRouteTarget = target;
  customNodeCount = 0;
  document.querySelector("#customNodeLayer").innerHTML = "";
  document.querySelector(".map-panel")?.classList.add("blank-route");
  document.querySelector(".map-panel")?.classList.remove("has-custom");
  document.querySelector("#nodeBuilder")?.classList.remove("open");
  document.querySelector("#routeIntake")?.classList.remove("open");
  document.querySelector("#blankWorkflowTarget").textContent = `${target} parsed. Add model cards or run compute check to continue.`;
  document.querySelector("#blankComputeStatus").textContent = "Compute status pending";
  if (window.lucide) window.lucide.createIcons();
  applyLanguage();
  showToast("Auto route drafted");
}

function checkComputeStatus(button) {
  showToast("Checking compute node status");
  button.innerHTML = '<span class="spinner"></span> Checking compute...';
  button.disabled = true;
  setTimeout(() => {
    document.querySelector("#blankComputeStatus").textContent = "Compute check failed: all Qiming HPC resources unavailable";
    button.innerHTML = '<i data-lucide="server-off"></i> Compute unavailable';
    button.disabled = false;
    button.classList.remove("success");
    button.classList.add("ghost");
    if (window.lucide) window.lucide.createIcons();
    applyLanguage();
    showToast("Compute nodes unavailable");
  }, 1100);
}

function exportResultsData() {
  const payload = {
    project: "Project_test_0423",
    target: automatedRouteTarget || "SARS-CoV-2 Spike RBD (PDB 6M0J), ACE2-facing epitope",
    metrics: {
      bindingPositiveRate: "18.8%",
      bliSprPositive: "9/48",
      bestMeasuredKd: "0.6 nM",
      mainQcLoss: "SEC aggregation",
      decision: "Round 2",
    },
    validationReadouts: [
      { step: "Expression screen", pass: "42/48", signal: "F2/F5 families express reliably" },
      { step: "Purification", pass: "36/48", signal: "Low-yield failures cluster in F1" },
      { step: "BLI / SPR", pass: "9/48", signal: "Best measured Kd: 0.6 nM" },
      { step: "SEC / aggregation", pass: "34/48", signal: "Exposed hydrophobic patches explain most QC loss" },
    ],
    candidates: candidates.map(([name, family, interfaceScore, predKd, plddt, mdDrift, expression, status, decision]) => ({
      name,
      family,
      interfaceScore,
      predKd,
      plddt,
      mdDrift,
      expression,
      status,
      decision,
    })),
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "bda_project_test_0423_results.json";
  link.click();
  URL.revokeObjectURL(url);
  showToast("Results data exported");
}

function handleProteinTemplateUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  const label = document.querySelector("#proteinTemplateName");
  const target = document.querySelector("#targetProteinInput");
  label.textContent = file.name;
  label.dataset.i18nEn = file.name;
  label.dataset.i18nZh = file.name;
  target.value = `Uploaded template: ${file.name}`;
  target.dataset.i18nValue = target.value;
  showToast("Protein template uploaded");
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function answerCopilotQuestion(question) {
  const normalized = question.toLowerCase();
  const matched = copilotResponses.find((item) => item.keywords.some((keyword) => normalized.includes(keyword)));
  return matched?.answer || "I would first check whether the requested change affects affinity, fold confidence, MD drift, expression risk, or wet-lab throughput. For this workflow, the safest next step is to preserve the c4361 motif, add developability penalties, and keep a diverse 48-64 candidate queue.";
}

function appendCopilotMessage(type, content, zhContent = content) {
  const chat = document.querySelector("#copilotChat");
  if (!chat) return;
  const quickActions = chat.querySelector(".quick-actions");
  const message = document.createElement("div");
  message.className = `message ${type}`;
  message.innerHTML = `<span data-i18n-en="${escapeHtml(content)}" data-i18n-zh="${escapeHtml(zhContent)}">${escapeHtml(currentLanguage === "zh" ? zhContent : content)}</span>`;
  chat.insertBefore(message, quickActions);
  chat.scrollTop = chat.scrollHeight;
}

function sendCopilotQuestion(question) {
  const cleanQuestion = question.trim();
  if (!cleanQuestion) return;
  const input = document.querySelector("#copilotInput");
  const translatedQuestion = zhText[cleanQuestion] || cleanQuestion;
  const answer = answerCopilotQuestion(cleanQuestion);
  appendCopilotMessage("user", cleanQuestion, translatedQuestion);
  appendCopilotMessage("bot", answer, zhText[answer] || answer);
  if (input) {
    input.value = "";
    input.focus();
  }
  applyLanguage();
}

function wireActions() {
  document.querySelectorAll("[data-route]").forEach((el) => {
    el.addEventListener("click", (event) => {
      event.preventDefault();
      setRoute(el.dataset.route);
    });
  });

  document.querySelectorAll("[data-agent-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.agentAction;
      const workspace = document.querySelector(".agent-workspace");
      const shouldClose = button.classList.contains("active") && workspace?.classList.contains("open");
      workspace?.classList.toggle("open", !shouldClose);
      document.querySelectorAll("[data-agent-action]").forEach((item) => {
        item.classList.toggle("active", !shouldClose && item.dataset.agentAction === action);
      });
      document.querySelectorAll("[data-agent-view]").forEach((view) => {
        view.classList.toggle("active", !shouldClose && view.dataset.agentView === action);
      });
    });
  });

  document.querySelector("#newRouteToggle")?.addEventListener("click", () => {
    const intake = document.querySelector("#routeIntake");
    intake?.classList.toggle("open");
    document.querySelector("#nodeBuilder")?.classList.remove("open");
    if (intake?.classList.contains("open")) {
      document.querySelector("#targetProteinInput")?.focus();
      showToast("New route panel opened");
    }
  });

  document.querySelector("#closeRouteIntake")?.addEventListener("click", () => {
    document.querySelector("#routeIntake")?.classList.remove("open");
  });

  document.querySelector("#autoRoute")?.addEventListener("click", draftAutoRoute);

  document.querySelector("#proteinTemplateUpload")?.addEventListener("change", handleProteinTemplateUpload);

  document.querySelector("#addNodeToggle")?.addEventListener("click", () => {
    const builder = document.querySelector("#nodeBuilder");
    builder?.classList.toggle("open");
    document.querySelector("#routeIntake")?.classList.remove("open");
    if (builder?.classList.contains("open")) showToast("Node builder opened");
  });

  document.querySelector("#closeNodeBuilder")?.addEventListener("click", () => {
    document.querySelector("#nodeBuilder")?.classList.remove("open");
  });

  document.querySelectorAll("[data-node-template]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedNodeTemplate = button.dataset.nodeTemplate;
      document.querySelectorAll("[data-node-template]").forEach((item) => {
        item.classList.toggle("active", item.dataset.nodeTemplate === selectedNodeTemplate);
      });
      renderNodePreview();
    });
  });

  document.querySelectorAll("[data-method]").forEach((checkbox) => {
    checkbox.addEventListener("change", renderNodePreview);
  });

  document.querySelector("#addCustomNode")?.addEventListener("click", addCustomNode);

  document.querySelector("#candidateSearch")?.addEventListener("input", (event) => {
    candidateSearchTerm = event.currentTarget.value;
    applyCandidateFilters();
  });

  document.querySelectorAll("[data-status-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      candidateStatusFilter = button.dataset.statusFilter;
      document.querySelectorAll("[data-status-filter]").forEach((item) => {
        item.classList.toggle("active", item.dataset.statusFilter === candidateStatusFilter);
      });
      applyCandidateFilters(true);
    });
  });

  document.querySelector("#showPriorityOnly")?.addEventListener("click", (event) => {
    priorityOnly = !priorityOnly;
    event.currentTarget.classList.toggle("active", priorityOnly);
    applyCandidateFilters(true);
  });

  document.querySelector("#exportCandidates")?.addEventListener("click", () => {
    showToast("Candidate CSV export prepared");
  });

  document.querySelector("#preparePackage")?.addEventListener("click", () => {
    showToast("Delivery package queued");
  });

  document.querySelector("#exportResults")?.addEventListener("click", exportResultsData);

  document.querySelector("#languageToggle")?.addEventListener("click", () => {
    currentLanguage = currentLanguage === "zh" ? "en" : "zh";
    localStorage.setItem("bda-language", currentLanguage);
    applyLanguage();
  });

  document.querySelectorAll("[data-suggestion]").forEach((button) => {
    button.addEventListener("click", () => {
      sendCopilotQuestion(button.dataset.suggestion);
    });
  });

  document.querySelector("#sendCopilotMessage")?.addEventListener("click", () => {
    sendCopilotQuestion(document.querySelector("#copilotInput")?.value || "");
  });

  document.querySelector("#copilotInput")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      sendCopilotQuestion(event.currentTarget.value);
    }
  });

  document.querySelector("#toggleCopilot").addEventListener("click", () => {
    document.querySelector("#copilotPanel").classList.toggle("open");
  });

  document.querySelector("#runWorkflow").addEventListener("click", (event) => {
    const button = event.currentTarget;
    checkComputeStatus(button);
  });
}

renderCandidates();
wireActions();
renderNodePreview();
setRoute((window.location.hash || "#experiments").replace("#", ""));
applyLanguage();
if (window.lucide) window.lucide.createIcons();
