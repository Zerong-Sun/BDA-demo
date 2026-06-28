# 网站操作与问题修复记录

## 已完成

1. 在 BDA Workbench 创建并最终恢复为 `SweetProtein_under100aa_20260625_final` 项目。
2. 提交 `<100 aa`、简单结构、单链优先的甜味蛋白 Research Brief。
3. DeepSeek 生成研究问题；执行 UniProt、RCSB、Europe PMC 和 FDA GRAS 检索。
4. 最终保存 77 条去重 evidence；LLM 综合标记为 `partial`，因为一个外部序列/结构比较请求返回空响应。
5. 下载 monellin、brazzein、mabinlin、curculin 的官方序列和结构。
6. 在网站完成序列全局比对和 PDB 结构叠合。
7. 生成 9 节点计算/实验 Workflow 和 8 阶段 Experiment Plan。
8. 完成 evidence/structure preparation gate，上传清洗后的 MNEI 输入并生成 RFdiffusion 提交预览。
9. 最终规划 provenance 为 `llm_validated`，模型为 `deepseek-v4-pro`，并通过 canonical route、
   registered model、现有参数键和可信脚本 renderer 四层校验。

## 发现并修复

- Research Builder 长任务结束前页面缺少阶段提示，且中断后无法恢复：增加阶段显示和“继续最近一次 Brief”。
- PDB 元数据正则错误导致链/残基为零：改用 PDB 固定列解析，并同步更新 target chain IDs。
- MNEI 模板 contig 写成 `[A1-90]`，与 2O9U 不符：改为清洗后的 `[A1-96]`。
- LLM 文献查询过宽，出现与甜味蛋白无关记录：为检索词强制加入甜味蛋白/候选 scaffold/TAS1R 上下文。
- 多条相同 Europe PMC/FDA evidence 重复：Research Run 保存前按来源、标识符和标题去重。
- 后端测试曾错误复用开发 SQLite，导致网站项目状态被清空：测试数据库改为按进程隔离的
  `/tmp/bda-tests-<pid>.sqlite3`，完成后清理；随后重新创建并导出最终项目。

## 当前阻塞

- `remote_lsf` 未配置 `BDA_LSF_PLUGIN_COMMANDS_JSON`，因此只生成可信脚本预览，不提交真实集群。
- Pentadin 缺少可独立确认的 UniProt/RCSB 序列与结构。
- 受体结合姿态和数值成功阈值仍需实验/原始文献审核，不能直接采用 LLM 建议。

## 最终实例

- Project：`proj_sweetprotein_under100aa_202606_dad57c`
- Research Brief：`brief_9ba546e05d26`
- Research Run：`research_run_4be71ea4a580`
- Workflow Plan：`plan_436ab13250bb`
- Workflow Run：`run_proj_sweetprotein_under100aa_202606_dad57c_60ee8863`
- Experiment Plan：`experiment_plan_85ab9d661a53`
- RFdiffusion node：`node_f1ba985523`
- RFdiffusion parameter checksum：
  `b669989219a605125cca4b6ce519dbd87abcff07a31770cde465c13e38aff7d7`
