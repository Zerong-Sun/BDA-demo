# 甜味蛋白研发 Copilot 与自动工作流实施计划

## 1. 目标

把当前“聊天 + 文献检索 + 手工创建 workflow 节点”升级为一个证据驱动的研发规划器。

用户只需要输入类似：

> 我要设计一个可食品应用的 AI 甜味蛋白，希望参考已有天然甜味蛋白、法规安全案例、甜味受体结合机制和现有序列/结构，并生成可编辑的计算设计与实验验证流程。

Copilot 应完成：

1. 澄清产品目标和约束。
2. 自动检索并整理法规、文献、序列、结构、受体机制和已有计算方法。
3. 形成带来源、证据等级和不确定性的 research dossier。
4. 基于 dossier 生成可编辑的计算设计 DAG 和湿实验计划。
5. 展开每个模型的完整参数、来源、默认值、推荐范围和修改理由。
6. 逐节点生成可审核的运行脚本，提交到 LSF 集群。
7. 监听任务状态，收集 artifact，满足 gate 后建议或启动下一步。
8. 接收湿实验结果，评价本轮并生成下一轮参数建议。

本功能不能把模型预测描述为已验证的甜味、受体激活、安全性或法规结论。

## 1.1 领域参考资料

第一版甜味蛋白领域模板参考用户提供的：

- `/Users/zero/Downloads/AI甜味蛋白_天然骨架_受体机制_计算设计与实验验证_2026-06-20 (1).md`

该文件作为 research seed，而不是无需复核的权威数据库。Copilot 摄取后应将内容拆分为 claim、citation、design recommendation 和 unresolved question；尤其对 2025—2026 年论文、预印本、企业商业状态及 FDA GRAS 状态，必须继续从论文原文、FDA 官方页面和数据库记录核验。

## 2. 当前能力与主要缺口

### 已有可复用能力

- Europe PMC、RCSB PDB、UniProt、Reactome 检索工具。
- 本地文献摄取、全文分块、claim/evidence 和人工审核。
- 模型插件注册表及 RFdiffusion、ProteinMPNN、AlphaFold2、Rosetta 参数 schema。
- Artifact、workflow DAG、端口校验、job、LSF adapter 和输出回收。
- Campaign 跨轮评价、参数 patch 和人工审批。
- 前端 Workflow、Research、Copilot 和任务状态界面。

### 需要补齐

以下缺口已在当前分支补齐：

- [x] 路线推荐由 DeepSeek LLM 结合证据、项目约束和注册插件生成；后端执行路线、节点与参数白名单校验。
- [x] “研究问题拆解 → 多源检索 → 证据矩阵 → 设计假设”使用持久化 Research Brief/Run/Question/Evidence/Finding/Hypothesis 对象。
- [x] FDA GRAS 官方记录队列、UniProt/PDB/Europe PMC 检索、序列全局比对和 PDB CA/Kabsch 结构叠合。
- [x] 项目级 design brief、assumption、risk、decision gate 和 success criteria，并进入 dossier 与版本化导出。
- [x] Inspector 支持参数分层编辑、schema 校验、推荐值 diff、脚本预览和 checksum 确认。
- [x] 可展开的实验包、阶段依赖 gate、结果 artifact、CSV/JSON/XLSX 模板和 Campaign 后续建议。
- [x] Workflow job 作为统一提交链路；Copilot 仅生成可审核计划，真实执行走受信任 renderer/adapter。
- [x] Research progress checkpoint、Job 状态轮询、产物 contract、显式重试、通知及自动/确认/建议三种推进策略。

## 3. 产品流程

### Phase A：需求解析

Copilot 把自然语言需求解析为 `ResearchBrief`：

- 产品用途：食品配料、研究试剂或其他。
- 目标性质：甜度、起效/后味、热稳定、pH 稳定、溶解性、表达宿主、成本。
- 设计类型：天然蛋白改造、结构域/表面重设计、从头设计或多路线并行。
- 受体与物种：默认要求用户确认人源甜味受体背景。
- 法规目标：GRAS 证据参考、食品应用地区、过敏原和安全评价范围。
- 项目规模：候选数量、预算、集群资源、时间线。
- 自动化等级：只生成建议、每节点确认、或 gate 通过后自动推进。
- 已有资料：用户上传的 PDF、表格、FASTA、PDB、链接和笔记。

不确定字段进入“待确认假设”，不会被静默补全为事实。

### Phase B：Research Dossier

规划器把任务拆为并行 research tracks：

1. **法规与安全先例**
   - 官方 FDA GRAS Notice/相关官方页面。
   - 其他地区监管材料按项目地区启用。
   - 区分“已提交”“无异议函”“批准用途/条件”和二手报道。

2. **天然甜味蛋白候选集**
   - 名称、物种、UniProt accession、序列、长度、二硫键、翻译后修饰、已知结构。
   - 甜味强度必须记录比较基准、浓度、pH、温度和测量方法。
   - 标记天然蛋白、工程突变体、融合体和纯计算候选。
   - 第一版骨架库至少覆盖：
     - single-chain monellin / MNEI：第一代稳定性、表达和感官优化主线。
     - brazzein-53/54：小型、耐热耐酸、二硫键约束明确的第一代并行路线。
     - thaumatin：成熟法规/商业参照和风味增强对照。
     - mabinlin：耐热储备骨架。
     - miraculin、neoculin、curculin：pH-responsive 第二代路线。
     - pentadin、Honey Truffle sweet protein：资料不足或新兴骨架观察列表。

3. **甜味受体机制**
   - 受体亚基、物种、构建体、实验结构或预测结构。
   - 结合区域、关键残基、结合姿态和激活机制。
   - 明确区分突变实验、功能 assay、docking、MD 和结构预测证据。
   - 默认研究对象为人源 TAS1R2/TAS1R3 异源二聚体，并分别记录 VFD、CRD、TMD 和二聚体界面证据。
   - Brazzein、monellin 和 thaumatin 不能共用一个未经验证的统一 docking pose。
   - 将“正电表面、多点接触和变构激活”保存为待具体蛋白验证的工作假设，而不是普遍定律。
   - 人/鼠受体差异必须进入实验设计，不能用小鼠甜味行为直接替代人体甜味结论。

4. **序列与结构比较**
   - FASTA 集合、结构集合、序列比对、结构叠合、保守位点和表面性质。
   - 建立“可保留位点、可设计位点、不可触碰位点、风险位点”约束。

5. **已有设计方法**
   - scaffold redesign、motif scaffolding、interface redesign、de novo design。
   - RFdiffusion、ProteinMPNN、Rosetta、结构预测和筛选方法的适用条件。
   - 记录论文真实使用参数，而非只生成模型默认参数。

6. **实验与转化**
   - 表达、纯化、结构/稳定性、受体功能、感官评价、安全性和法规资料需求。
   - 将发酵宿主、分泌表达、正确折叠和纯化成本作为序列设计约束，而不是设计完成后的附加检查。
   - 第一应用场景默认优先饮料；烘焙和巧克力需要额外评估糖的体积、质构和加工功能。

每个结论保存：

- claim；
- evidence excerpt；
- DOI/PMID/PDB/UniProt/官方 URL；
- 来源类型；
- 证据等级；
- 适用条件；
- 冲突证据；
- Copilot synthesis；
- review status。

### Phase C：设计路线生成

规划器至少比较三条路线，而不是默认把所有任务都塞进 binder workflow：

1. **天然甜味蛋白定向改造**
   - 适合已有甜味和可用结构/序列的 scaffold。
   - 优先进行界面、稳定性、溶解性和表达优化。
   - 默认第一代主线比较 single-chain monellin 与 brazzein-53：
     - monellin：重点优化热稳定、单链 linker、分泌表达、后味和加工兼容性。
     - brazzein：重点优化表面残基、二硫键正确形成、表达宿主适配和专利空间。

2. **受体结合表面重设计**
   - 保留天然 fold 或功能 motif，使用 partial diffusion / inpainting / Rosetta design。

3. **从头设计**
   - 仅在受体结合假设和可验证约束足够明确时启用。
   - RFdiffusion 生成受约束骨架，ProteinMPNN 设计序列，结构预测和 Rosetta 进行多级筛选。
   - 第一代产品默认不推荐完全 de novo；只有用户明确选择高风险探索路线，且 receptor epitope、positive controls 和功能 assay 已定义时才进入正式 workflow。

Copilot 输出路线比较表，包括依据、预期收益、主要风险、所需数据、计算成本和实验可验证性。用户选择后才生成正式 workflow draft。

## 4. 建议的计算 Workflow

默认 DAG：

`需求与证据审核`
→ `受体/模板结构准备`
→ `设计约束生成`
→ `天然 scaffold redesign / partial diffusion / de novo RFdiffusion 分支`
→ `ProteinMPNN`
→ `单体折叠、二硫键检查与复合物预测`
→ `Rosetta relax/interface analysis`
→ `序列、表达、分泌、安全性预筛与 developability filters`
→ `候选聚类与多样性选择`
→ `人工 design review gate`
→ `湿实验包`

可选并行分支：

- 天然蛋白基线与已知突变体作为 positive controls。
- single-chain monellin 与 brazzein 双骨架并行。
- 多 scaffold 并行。
- RFdiffusion 与 Rosetta redesign 并行。
- 不同结构预测器交叉验证。
- 不同受体结构/构象 ensemble 评估。

每个节点都应包含：

- 输入 artifact 和来源；
- 参数 schema、默认值、推荐值、允许范围和依据；
- 资源需求、队列和预计时间；
- 生成脚本预览；
- 输出 artifact contract；
- 成功/失败 gate；
- 重试策略；
- 下游节点；
- 是否允许自动推进。

## 5. RFdiffusion 节点专项设计

第一批实现应先把 RFdiffusion 节点做完整，因为它最能验证“研究证据 → 约束 → 参数 → 脚本 → 集群”的闭环。

甜味蛋白模板中，RFdiffusion 节点必须先选择运行模式：

- `scaffold_partial_diffusion`：从 monellin、brazzein 等天然骨架局部改造。
- `motif_or_surface_scaffolding`：保留已有功能表面或关键残基。
- `receptor_binder_de_novo`：面向 TAS1R2/TAS1R3 指定胞外区域的高风险从头设计。

不得仅凭“提高 binding score”自动扩大正电荷或改写整个甜味蛋白表面；需要同时约束 fold、二硫键、已知功能残基、表达风险、非特异结合和感官假设。

### 参数分层

- Basic：输入结构、设计模式、设计数量、长度范围、hotspot、输出前缀。
- Advanced：contig、partial diffusion、inpaint、noise scale、diffusion steps、guiding potentials、checkpoint、symmetry、seed。
- Expert：完整 Hydra override JSON/YAML。

### 每个参数的附加元数据

- `value`
- `default`
- `recommended_range`
- `source`：模型文档、论文、导入脚本或 Copilot 推断。
- `reason`
- `confidence`
- `dependencies`
- `validation_rules`
- `user_modified`

### 脚本生成

由受信任 renderer 根据插件 manifest 和已验证参数生成：

- LSF directives；
- 环境/module/container setup；
- artifact staging；
- RFdiffusion command；
- manifest 和日志输出；
- checksum；
- expected outputs；
- retry-safe 工作目录。

LLM 只能产生结构化参数建议，不能直接拼接任意 shell。用户审核脚本后才能提交。

## 6. 湿实验节点设计

湿实验节点在画布上显示为一个可展开的 `Experiment Plan` 容器，内部是可编辑的阶段、检查项和结果模板。

### 建议阶段

1. **构建与表达可行性**
   - 构建设计、表达宿主选择、small-scale expression screen。
   - 对照包括天然甜味蛋白/已知基线、阴性蛋白和工艺空白。

2. **纯化与质量**
   - 纯度、分子量确认、SEC 单分散性、聚集、必要时二硫键/寡聚状态。

3. **稳定性与配方窗口**
   - 热稳定、pH 稳定、储存稳定、溶解性和冻融稳定。

4. **受体结合或功能**
   - 单纯结合测量不能替代受体激活。
   - 是否做 BLI/SPR 取决于是否有合理的受体构建体和结合 assay。
   - 核心应包含适当的细胞受体功能 assay，并记录剂量反应、重复、阳性/阴性对照和选择性。
   - 推荐结果字段包括 EC50、Emax、Hill coefficient、相对阳性对照活性、pH 依赖、受体亚基依赖和抑制剂敏感性。
   - 对照模板应支持空载细胞、单亚基、人源完整受体、物种/嵌合受体、已知甜味蛋白及小分子阳性对照。

5. **甜味评价**
   - 先采用非人体的分析/功能证据做筛选。
   - 人体感官评价必须在合适的伦理、知情同意、样品安全和法规条件下单独审批。
   - 输出相对甜度时必须绑定参照物、浓度、基质、温度、pH 和统计方法。
   - 计划模板包含识别阈值、等甜浓度、三角测试、描述性评价、time-intensity、后甜及苦/涩/金属异味。

6. **安全与转化**
   - 计算过敏原/毒性筛查只能作为风险筛选。
   - 是否需要动物实验或人体研究由用途、暴露、安全证据、监管路径和伦理审查决定，不由 Copilot 自动下结论。
   - Copilot 生成“需要咨询的法规/伦理问题清单”，不生成未经批准的执行指令。

7. **食品基质与工艺**
   - 饮料：pH、巴氏杀菌/UHT、碳酸、茶多酚、金属离子和货架期。
   - 乳品/蛋白饮料：蛋白相互作用、沉淀、黏度、热处理和风味遮蔽。
   - 发酵评价不能只看蛋白滴度，应增加：

     `effective sweetness titer = protein titer × correct folding fraction × relative sweetness`

   - 下游计划记录总回收率、纯度、宿主蛋白、残留 DNA、树脂/膜性能和单位成本。

### 实验计划 UI

- 阶段折叠/展开。
- 每个 assay 可编辑目的、样本、对照、读数、通过标准、依赖和负责人。
- 支持上传 SOP 引用，但默认只展示高层计划。
- 支持 CSV/XLSX 结果模板和 artifact 回传。
- 结果回传后触发 Campaign 评价，不自动执行现实世界实验。

## 7. 后端设计

### 新增核心对象

- `research_briefs`
- `research_questions`
- `research_runs`
- `research_findings`
- `evidence_links`
- `design_hypotheses`
- `workflow_plans`
- `workflow_plan_nodes`
- `parameter_recommendations`
- `decision_gates`
- `experiment_plans`
- `experiment_plan_steps`
- `run_automation_policies`
- `notifications`
- `protein_scaffolds`
- `receptor_regions`
- `regulatory_precedents`
- `assay_templates`
- `food_matrix_profiles`

所有规划对象都要版本化；用户修改后保留原始 Copilot 建议和 diff。

### 新增服务

- `ResearchPlannerService`
- `EvidenceSynthesisService`
- `ProteinLandscapeService`
- `WorkflowPlannerService`
- `ParameterRecommendationService`
- `ScriptRendererService`
- `RunCoordinatorService`
- `ExperimentPlannerService`

### 新增/扩展工具

- 官方法规检索与证据导入。
- UniProt 完整 FASTA、feature、cross-reference 获取。
- PDB polymer entity/chain/ligand/interface 详情。
- 序列多重比对和结构叠合任务。
- 用户资料导入、去重和 citation parsing。
- 模型参数的文献观察值与本地脚本观察值检索。
- workflow draft 创建、参数 patch、单节点脚本预览。
- FDA GRAS Notice 官方记录解析，并区分 no-questions letter、自我 GRAS、已提交和企业宣称。
- 甜味蛋白 scaffold dossier：天然来源、链组成、二硫键、结构、已知突变、甜味特征、生产宿主和专利风险。
- TAS1R2/TAS1R3 receptor map：结构版本、亚基、domain、chain、物种、构建体和证据支持的候选接触区域。

### 规划 API

- `POST /copilot/research-briefs`
- `POST /copilot/research-briefs/{id}/plan`
- `POST /copilot/research-runs/{id}/start`
- `GET /copilot/research-runs/{id}`
- `PATCH /copilot/research-findings/{id}/review`
- `POST /copilot/workflow-plans/{id}/materialize`
- `PATCH /workflow-nodes/{id}/parameters`
- `POST /workflow-nodes/{id}/script-preview`
- `POST /workflow-nodes/{id}/submit`
- `PATCH /workflow-runs/{id}/automation-policy`
- `GET/PATCH /experiment-plans/{id}`

## 8. 前端设计

### Copilot Research Builder

使用分步界面：

1. Goal
2. Constraints
3. Existing materials
4. Research tracks
5. Evidence review
6. Route comparison
7. Workflow draft

Research Dossier 用 tab 展示：

- Regulatory
- Natural proteins
- Receptor mechanism
- Sequences
- Structures
- Design methods
- Experimental strategy
- Risks and unknowns

首版甜味蛋白模板增加一个 `Scaffold comparison` 视图，默认比较：

- single-chain monellin
- brazzein-53/54
- thaumatin
- mabinlin
- pH-responsive proteins
- de novo receptor binder

比较维度包括甜味证据、结构资料、受体机制、表达/分泌、二硫键或糖基化复杂度、食品稳定性、法规先例、专利拥挤度和研发风险。

### Workflow 改造

- Copilot 生成的是后端持久化 `workflow_plan`，不再由前端硬编码节点。
- 节点 Inspector 支持 Basic / Advanced / Expert 参数编辑。
- 展示 Copilot 推荐值与用户当前值的 diff。
- 参数变化后实时校验并重新生成脚本预览。
- 节点状态增加 `awaiting_review`、`ready`、`blocked`、`waiting_external_result`。
- Experiment Plan 节点可展开为内部阶段列表。
- 顶部显示自动推进策略和当前 gate。

## 9. 调度与自动推进

推荐状态机：

`draft`
→ `awaiting_review`
→ `ready`
→ `queued`
→ `running`
→ `collecting_outputs`
→ `evaluating_gate`
→ `completed`

异常状态：

- `blocked`
- `failed_retryable`
- `failed_terminal`
- `waiting_external_result`
- `cancelled`

自动推进规则：

- 默认每个真实计算节点提交前都需要确认。
- 用户可对同一 workflow 开启“后续节点 gate 通过后自动提交”。
- 湿实验节点永远只进入等待结果状态。
- 任务完成后进行 artifact contract、文件完整性和质量 gate 检查。
- gate 不通过时生成解释、重试建议和参数 patch，不覆盖历史 job。
- 通知支持站内提醒，后续可扩展邮件/企业消息。

## 10. 分阶段实施

### Milestone 1：研究 brief 与 dossier

- 新增 brief、question、finding、evidence 数据模型。
- 将现有 Europe PMC/PDB/UniProt/本地资料统一为 research run。
- 实现甜味蛋白 research track 模板。
- 将用户提供的甜味蛋白资料作为首个可追溯 seed document 摄取，并把其中引用解析为待核验 source queue。
- 建立 monellin、brazzein、thaumatin、mabinlin、miraculin/neoculin 和 de novo 路线比较卡。
- 实现证据矩阵和人工审核 UI。

验收：输入甜味蛋白目标后，系统生成可追溯的问题树和 dossier；所有事实性结论可回到来源。

### Milestone 2：证据驱动 workflow planner

- 后端生成结构化 `workflow_plan`。
- 支持三类设计路线比较。
- 将 plan materialize 为真实 DAG。
- 新增 assumption、risk、gate 和 success criteria。
- 默认提出“single-chain monellin 定向改造”和“brazzein 定向改造”两条第一代路线，并将 de novo 标为高风险探索分支。

验收：不再依赖前端硬编码 `buildRecommendedWorkflow()`；同一 brief 可生成和比较多条路线。

### Milestone 3：RFdiffusion 完整参数与脚本闭环

- 完善参数目录和依赖校验。
- 新增可编辑参数 Inspector。
- 新增受信任脚本 renderer 和 LSF preview。
- 单节点确认、提交、轮询、artifact 回收和 gate。

验收：用户能审阅全部 RFdiffusion 参数，修改后生成确定性脚本并提交集群；完成后自动注册骨架 artifact。

### Milestone 4：后续计算链与自动推进

- ProteinMPNN、结构预测、Rosetta 和 filters 接入同一 planner。
- 增加单体/复合物、多模型共识和候选聚类节点。
- 增加 workflow automation policy、通知和失败恢复。

验收：RFdiffusion 输出可自动成为下游输入；每一步均保留参数、脚本、日志、artifact 和 lineage。

### Milestone 5：Experiment Plan

- 实验容器节点、阶段模板、结果模板和 gate。
- 表达/纯化/稳定性/受体功能/甜味评价/安全转化模块。
- 增加食品基质、发酵放大和下游成本模块。
- 结果上传后接入 Campaign 评价与下一轮建议。

验收：实验节点可以展开、编辑和回传结果；系统能依据结果提出下一轮计算参数 patch。

### Milestone 6：硬化与领域扩展

- 权限、审计、成本预算、并发限制和数据隔离。
- dossier/export、项目模板和可复现报告。
- 把甜味蛋白模板抽象为可复用的“领域 research workflow template”。

## 11. 测试与验收策略

- 单元测试：需求解析、参数校验、证据评级、gate、状态机和脚本渲染。
- Contract test：每个模型的 input/output manifest。
- 集成测试：mock research source、mock LSF、失败重试和 artifact lineage。
- 前端测试：参数分层、diff、实验节点展开和人工确认。
- E2E：从“设计甜味蛋白”输入到 RFdiffusion 脚本预览，再到 mock 集群输出进入 ProteinMPNN。
- 科学质量测试：固定 benchmark brief，检查关键 research tracks 是否齐全、引用是否可追溯、预测与实验证据是否正确区分。
- 安全测试：prompt injection、恶意上传、任意 shell、路径穿越、秘密泄露和未经确认提交。

## 12. 第一轮建议实施范围

建议第一轮只实现一条完整的垂直切片：

1. 创建甜味蛋白 Research Brief。
2. 摄取用户提供的 Markdown 资料，并将 35 项参考资料形成待核验队列。
3. 执行 FDA/PDB/UniProt/Europe PMC 检索，复核法规状态、受体结构和关键机制。
4. 生成 single-chain monellin、brazzein、thaumatin/pH-responsive 与 de novo 路线比较。
5. 默认推荐用户先选择 monellin 或 brazzein 定向改造；允许显式选择 de novo。
6. 创建可编辑的 scaffold redesign / partial RFdiffusion 节点。
7. 展示全部参数、保留位点、二硫键约束和推荐依据。
8. 生成并审核 LSF 脚本。
9. 提交 mock/真实 LSF。
10. 收回 backbone artifact。
11. 将下一个 ProteinMPNN 节点置为 `awaiting_review` 并提醒用户。

这条垂直切片验证通过后，再扩展自动 ProteinMPNN、结构预测、Rosetta 和完整实验计划。

## 13. 实施完成记录（2026-06-25）

本分支已完成计划中的首个可运行版本：

- DeepSeek `deepseek-v4-pro` OpenAI-compatible 接入、真实连通性验证、结构化 research decomposition、证据综合和路线规划。
- LLM 输出经过 canonical route、registered plugin、existing parameter key 和 trusted renderer 四层校验；失败时回退确定性模板。
- Research Brief、问题树、多源 Research Run、证据审核、设计假设和 Markdown/JSON dossier 导出。
- 用户 Markdown seed 的摄取、更新、分块、引用队列和本地检索。
- monellin、brazzein、pH-responsive 和 de novo 路线比较，以及后端持久化 workflow plan。
- RFdiffusion → ProteinMPNN → 结构预测 → Rosetta → filters → selection → review gate → Experiment Plan 的真实 DAG。
- RFdiffusion 参数白名单、范围校验、推荐来源/范围/当前值 diff、确定性脚本预览、checksum 确认和集群提交。
- artifact 项目隔离、上游 gate、输出 lineage、自动推进策略、站内通知和失败重试建议。
- 模型输出 manifest 与必需端口 contract 校验；缺失产物会阻止自动推进并保留失败原因。
- Job Drawer 中的失败/取消任务显式重试，新 job 保留旧 job 历史和参数 checksum。
- Research Dossier 中的 FASTA 全局比对、保守参考位点，以及项目 PDB 的 CA/Kabsch 结构叠合。
- 可展开的八阶段 Experiment Plan，完整编辑样品、对照、读数、判定标准、依赖、负责人和备注。
- 实验结果 artifact、CSV/JSON/XLSX 结果模板，以及完成后的 workflow/Campaign 同步。
- Workflow Plan v1/v2 版本链、supersedes 关系，以及包含证据、参数建议和 decision gate 的可复现 dossier 导出。
- 甜味蛋白 scaffold、受体区域、法规先例、assay 和食品基质领域目录初始化。

安全边界保持不变：预测结合不等于甜味；人体感官、动物研究和安全研究不会自动执行，必须经过独立伦理、法规和专业审核。

验收结果：

- 后端：111 tests passed，coverage 74.47%。
- 前端：16 tests passed。
- 全新数据库 Alembic `upgrade head`、TypeScript production build 和 `git diff --check` 均通过。
- 测试数据库已与开发数据库隔离，避免验收测试清空浏览器项目状态。
- 已通过网站完成 `<100 aa` 甜味蛋白实例验收，并将官方序列/结构、研究 dossier、
  比较结果、实验模板、清洗脚本和 RFdiffusion 提交预览归档到
  `deliverables/sweet_protein_under100aa_20260625/`。
- 新建 `SweetProtein_RFdiffusion_100x2_20260626` 持久化项目，建立
  monellin 单链 linker 与 brazzein 保守 partial diffusion 两条独立 Workflow Run；
  每条路线配置 100 个骨架，并保存输入 PDB、参数 checksum、input manifest、
  LSF 脚本、可信 wrapper、失败/重试历史和后续 ProteinMPNN 正电表面约束。
- Workflow 页面支持在同一项目内切换多个 run，便于后续打开项目继续选择
  monellin 或 brazzein 输出进入 ProteinMPNN。

实现边界：

- 结构叠合当前按 PDB 中 CA 原子的文件顺序配对，界面明确提示正式设计 gate 前必须复核 chain/residue mapping。
- 人体感官、动物研究、安全研究和法规提交只生成计划与审批要求，不由系统自动执行。
- 邮件/企业消息通知、外部 ELN/LIMS 和真实机构伦理审批仍属于部署集成项，不影响本地闭环验收。
