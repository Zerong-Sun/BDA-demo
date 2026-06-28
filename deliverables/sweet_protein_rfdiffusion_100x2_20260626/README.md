# 甜味蛋白 RFdiffusion 100+100 第一轮项目包

日期：2026-06-26

网站项目：`SweetProtein_RFdiffusion_100x2_20260626`

Project ID：`proj_sweetprotein_rfdiffusion_100x2_160d28`

Research Brief：`brief_43c62a58c4ec`

## 路线

### 主路线：monellin 单链 linker

- Workflow Plan：`plan_cf8b1982b14d`
- Workflow Run：`run_proj_sweetprotein_rfdiffusion_100x2_160d28_449a8216`
- RFdiffusion node：`node_ae2d3b9519`
- 最新提交记录：`job_8b6d4668af4d`
- 输入为从 2O9U/MNEI 还原的天然 B 链 50 aa 与 A 链 44 aa motif。
- 原 MNEI Gly-Phe linker 从输入中移除。
- Contig：`[A1-50/2-4/B1-44]`，输出为一条 96–98 aa 链。
- `num_designs=100`，`T=50`，`partial_T=0`，noise `0.5/0.5`。
- 参数 checksum：
  `4c02277c9f4fe82ad83d48d478f615b19f0fe1c84b1efb6b1d2cf2fba248e333`

### 并行路线：brazzein

- Workflow Plan：`plan_c9471f0d633e`
- Workflow Run：`run_proj_sweetprotein_rfdiffusion_100x2_160d28_bbe4a091`
- RFdiffusion node：`node_080b9aac0f`
- 最新提交记录：`job_3730ec5f78a7`
- 输入为 4HE7 清洗后的 53 个建模残基。
- Contig：`[A1-53]`。
- `num_designs=100`，`T=50`，`partial_T=5`，noise `0.5/0.5`。
- `provide_seq=[2,14,20,24,35,45,47,50]` 保留 8 个建模半胱氨酸位点。
- 参数 checksum：
  `0bf0964860bf7bc57e782df03346d73951b118cf7b4aaae881fa84e244be6ee4`

## 提交状态

两条路线都已通过平台参数预览与 checksum 确认，并创建真实提交记录。
当前两次最新提交均为 `failed`，原因是本机无法通过 SSH 到达 `qm` LSF
入口。平台保留了 job 历史、输入 manifest、LSF 脚本和可信 wrapper；
网络/VPN 或跳板恢复后可从项目页面重试，不需要重建参数。

## 目录

- `monellin/`：主路线输入 PDB、manifest、LSF 脚本和可信 wrapper。
- `brazzein/`：并行路线输入 PDB、manifest、LSF 脚本和可信 wrapper。
- `library/`：完整参考资料库、第一轮参数说明和 ProteinMPNN 正电表面约束。

## 重要边界

RFdiffusion 仅生成骨架。正电表面属于 ProteinMPNN、结构预测、电势计算和
受体功能筛选阶段。不能通过增加总净正电荷替代位置特异的电荷设计。
