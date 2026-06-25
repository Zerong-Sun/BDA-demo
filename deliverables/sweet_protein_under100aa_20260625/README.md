# AI 甜味蛋白（<100 aa）研发复用包

创建日期：2026-06-25

最终项目：`SweetProtein_under100aa_20260625_final`

Project ID：`proj_sweetprotein_under100aa_202606_dad57c`

Research Brief：`brief_9ba546e05d26`

Workflow Run：`run_proj_sweetprotein_under100aa_202606_dad57c_60ee8863`

## 推荐结论

- 主路线：single-chain monellin / MNEI（RCSB 2O9U），97 aa 序列、96 个建模残基，单链且无二硫键网络。
- 并行路线：brazzein（UniProt P56552 / RCSB 4HE7），54 aa、4 对二硫键，耐酸耐热但依赖正确氧化折叠。
- mabinlin-2：成熟链为 33 aa + 72 aa 的异源双链，不符合“尽量单链”；适合作为耐热机制参考。
- curculin-1：成熟链约 114 aa 且形成二聚体，不满足 `<100 aa` 硬约束。
- pentadin：未在本次 UniProt/RCSB 官方检索中找到可独立确认的序列或结构，保留为待核验对象；不得用同植物来源的 brazzein 条目代替。

当前 RFdiffusion 预览使用清洗后的 MNEI `A1–96` 完整骨架进行 partial diffusion。
未自动提交集群，因为本地 `remote_lsf` 尚未配置受信任的插件命令映射。

最终 Research Run 为 `partial`：保存 77 条去重证据，DeepSeek
`deepseek-v4-pro` 完成受控综合与路线规划；一个外部序列/结构比较请求返回空响应。
缺失部分已由本包中的 UniProt/RCSB 官方下载、本地序列清单和结构比较补齐。

## 目录

- `inputs/`：原始提示、用户参考资料及比较请求。
- `sequences/`：UniProt 与 RCSB FASTA。
- `structures/`：RCSB 原始 PDB 与 RFdiffusion 清洗输入。
- `evidence/`：UniProt/RCSB 官方 JSON 和来源表。
- `analysis/`：候选比较、序列清单与设计建议。
- `exports/`：首次浏览器运行的导出。
- `exports/final/`：恢复后最终实例的 ID、Research Dossier、Research Run、Workflow、
  实验模板、比较结果和 RFdiffusion 提交预览。
- `scripts/`：可重复执行的序列清单与 PDB 清洗脚本。

## 复现

```bash
python scripts/build_sequence_inventory.py
python scripts/clean_pdb_for_rfdiffusion.py \
  structures/2O9U.pdb structures/2O9U_MNEI_clean_A1-96.pdb --chain X
```

RFdiffusion 实际模型命令见
`exports/final/rfdiffusion_submission_preview.json` 的 `model_command_preview`；
通用容器入口 `command` 不是模型参数脚本。

预测结合、序列相似性或结构 RMSD 均不等于甜味、受体激活、安全性或法规可用性。
