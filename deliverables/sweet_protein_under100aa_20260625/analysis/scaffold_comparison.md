# 天然甜味蛋白候选比较

| 候选 | 官方序列/结构 | 成熟形态 | 长度 | 二硫键 | 与需求匹配 |
|---|---|---:|---:|---:|---|
| MNEI / single-chain monellin | RCSB 2O9U；天然链 P02881/P02882 | 工程单链 | 97 aa FASTA；96 个建模残基 | 无必需二硫键网络 | 高：单链、<100 aa、结构清楚 |
| Brazzein | UniProt P56552；RCSB 4HE7 | 单链 | 54 aa；4HE7 建模 53 aa | 4 对 | 高：极短、耐酸热；氧化折叠是主要风险 |
| Mabinlin-2 | UniProt P30233；RCSB 2DS2 | A/B 双链 | 33 aa + 72 aa | 2 对链间 + 2 对链内 | 中低：各链 <100 aa，但不是单链 |
| Mabinlin-1/3 | UniProt P80351/P80352 | A/B 双链 | 32 aa + 72 aa | 4 对 | 中低：可作稳定性参照 |
| Curculin-1 | UniProt P19667；RCSB 2DPF | 约 114 aa 单体，二聚体工作 | 114–115 aa | 链内及链间 | 低：超过 100 aa 且寡聚 |
| Pentadin | 本次官方数据库检索未确认 | 未确认 | 未确认 | 未确认 | 暂不进入设计；继续查原始分离/测序文献 |

## 序列比较解释

网站的全局配对结果以 MNEI 为参考：

- brazzein：identity 35.9%，coverage 54.6%；
- mabinlin-2 B 链：identity 20.8%，coverage 74.2%；
- mabinlin-2 A 链：identity 48.5%，coverage 34.0%；
- curculin-1：identity 21.6%，coverage 100%。

这些蛋白属于不同折叠和链组织，低复杂度/带电残基会抬高局部 identity。
这些数字只能用于初步描述，不能据此定义共同甜味 motif。

## 结构比较解释

网站按 CA 文件顺序进行 Kabsch 叠合：

- 2O9U ↔ 4HE7：RMSD 12.821 Å，coverage 39.6%；
- 2O9U ↔ 2DS2：RMSD 20.626 Å，coverage 70.9%；
- 2O9U ↔ 2DPF：RMSD 17.627 Å，coverage 30.2%。

由于没有进行同源残基映射，以上 RMSD 仅证明整体折叠不相同，不能作为设计 gate。
正式结构约束应在每个 scaffold 内部进行同源突变体叠合。
