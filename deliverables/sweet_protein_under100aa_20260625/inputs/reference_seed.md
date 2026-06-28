# AI 甜味蛋白完整探索：天然骨架、受体结合机制、计算设计、实验验证与文献图谱

> 版本：2026-06-20
> 重点：AI 甜味蛋白研发，而不是一般代糖市场综述
> 核心问题：哪些天然甜味蛋白可作为 AI 设计骨架？它们如何作用于甜味受体？现有 AI/计算设计产品改造了什么？成功开发一个 AI 甜味蛋白需要完成哪些实验？

---

## 0. 一句话结论

AI 甜味蛋白最现实的路线不是从零创造一个完全陌生的“糖蛋白”，而是以 **monellin、brazzein、thaumatin、miraculin/neoculin 类味觉修饰蛋白**作为天然模板，围绕 **TAS1R2/TAS1R3 甜味受体的胞外结构域和变构激活机制**进行计算设计，再用 **受体细胞实验、人体感官、食品基质测试、发酵放大、毒理和监管**逐层验证。

目前真正接近商业化的 AI/计算设计代表是：

- **Amai Proteins 的 Sweelin**：以 monellin 为骨架，经 AI/计算蛋白设计改造，由 *Komagataella phaffii* 发酵生产，已获得 FDA GRN 1269 无异议函。
- **Oobli 的改造型 monellin**：由 *K. phaffii* P-MON-040 生产，FDA GRN 1183 无异议。
- **计算稳定化 monellin 研究**：例如使用 PyRosetta ΔΔG 计算得到 boiling-resistant single-chain monellin。
- **de novo receptor binder 预印本**：2026 年 arXiv 报道用 RFdiffusion、ProteinMPNN、Boltz-1、MM/GBSA 设计靶向 TAS1R2 的潜在甜味蛋白，但仍主要是计算结果，还没有完成表达、受体激活、人体感官和监管验证。

---

# 一、天然甜味蛋白：AI 设计的天然骨架库

AI 甜味蛋白不能凭空开始。最可靠的起点是已经被人体感知为甜、并且已有结构、突变或受体作用资料的天然蛋白。

## 1.1 经典甜味蛋白和味觉修饰蛋白总表

| 蛋白 | 天然来源 | 结构特征 | 甜味/味觉特征 | 商业成熟度 | 适合 AI 改造的价值 |
|---|---|---|---|---|---|
| **Thaumatin** | 西非 katemfe 果实，*Thaumatococcus daniellii* | 约 207 aa，约 22 kDa，多二硫键，强正电表面 | 甜度高，后甜长，常用于风味增强 | 已成熟商业化，E957 | 适合风味修饰、后味改善和复配，不一定适合作第一代新序列 |
| **Brazzein** | 西非 oubli fruit，*Pentadiplandra brazzeana* | 53/54 aa，约 6.5 kDa，4 对二硫键 | 小、强甜、耐热、耐酸 | 早期商业化，多个 FDA GRAS 案例 | 适合第一代产业化，尤其饮料；但专利拥挤 |
| **Monellin** | Serendipity berry，*Dioscoreophyllum cumminsii* | 天然双链；工程常改为单链 MNEI/scMonellin | 甜度极高，但天然形式稳定性不足 | 早期商业化 | 最适合 AI 改造稳定性和感官，Sweelin 即此路线 |
| **Mabinlin** | 中国云南植物 *Capparis masaikai* 种子 | A/B 两链，二硫键稳定；mabinlin II 耐热 | 甜度低于 brazzein/thaumatin，但耐热性突出 | 未商业化 | 可作为耐热新骨架研究储备 |
| **Pentadin** | *Pentadiplandra brazzeana* | 资料较少，蛋白性质确认较早 | 约数百倍甜，研究少 | 未商业化 | 资料不足，短期不适合做商业主线 |
| **Curculin** | *Curculigo latifolia* | 二聚体/异源亚基相关 | 自身甜味 + 酸味转甜 | 未商业化 | 机制独特，但亚基装配复杂 |
| **Neoculin** | *Curculigo latifolia* | 异源二聚体，酸性条件下味觉修饰 | 中性下可表现不同，酸性下转甜 | 未商业化 | 适合酸饮料专用味觉修饰蛋白探索 |
| **Miraculin** | 神秘果 *Synsepalum dulcificum* | 糖蛋白，寡聚体 | 本身不甜或弱甜；酸性条件下酸转甜 | 果粉/片剂商业化，重组纯蛋白未成熟 | 适合味觉修饰研究，不适合作通用高倍甜味剂 |
| **Honey Truffle Sweet Protein / HT-AC** | 匈牙利蜜块菌相关蛋白 | 新蛋白骨架，公开结构资料相对少 | 企业称甜度高、后味少 | MycoTechnology Zukora 早期商业化 | 新骨架，可能避开 brazzein/monellin 竞争 |

## 1.2 天然甜味蛋白的共同规律

不同甜味蛋白没有统一的序列和折叠类型，但常见共同特征包括：

1. **表面带正电区域明显。** Thaumatin、brazzein、monellin 等甜味蛋白虽然结构不同，但许多研究指出其正电荷表面区域与甜味受体的酸性或极性表面可能形成多点相互作用。
2. **甜味依赖整体折叠，而不是短线性序列。** 失去二硫键、变性或聚集后甜味往往下降。
3. **与小分子甜味剂不同，甜味蛋白更像大分子变构配体。** 它们通常不简单进入小分子糖类的经典口袋，而是通过 T1R2/T1R3 的胞外结构域表面或 CRD 区域稳定受体激活构象。
4. **种属差异明显。** 一些甜味蛋白对人类、旧大陆猴和猿有效，但对小鼠等啮齿类无效或弱效。因此只做小鼠行为实验并不能直接证明人体甜味。

---

# 二、甜味受体：结合位点、作用方式与研究方法

## 2.1 受体组成

人体甜味受体是 **TAS1R2/TAS1R3** 异源二聚体，属于 C 类 G 蛋白偶联受体。

每个亚基大致包括：

```text
N-terminal Venus Flytrap Domain, VFD
→ Cysteine-Rich Domain, CRD
→ Seven-Transmembrane Domain, 7TM/TMD
→ Intracellular G-protein signaling region
```

甜味信号链可概括为：

```text
甜味分子或甜味蛋白结合 TAS1R2/TAS1R3
→ 受体胞外结构域构象改变
→ 跨膜区激活
→ G 蛋白信号
→ PLCβ2 / IP3 / Ca²⁺ 相关通路
→ 味觉细胞去极化
→ ATP 等递质释放
→ 味觉神经传入
→ 大脑感知甜味
```

## 2.2 小分子甜味剂与甜味蛋白的结合差异

### 小分子甜味剂

小分子甜味剂可以结合在：

- TAS1R2 的 VFD；
- TAS1R3 的 VFD；
- TAS1R3 的 TMD；
- 其他变构区域。

例如 sucralose、aspartame 等研究显示，小分子甜味剂可进入 VFD 或跨膜结构区域。

### 甜味蛋白

甜味蛋白体积较大，不太可能像小分子一样完全进入 VFD 内部口袋。早期理论提出甜味蛋白可能通过“secondary binding site”或变构位点稳定受体的激活构象。后续突变、嵌合受体、对接和分子动力学研究支持甜味蛋白主要作用于受体胞外表面，尤其涉及：

- TAS1R2 的 VFD/胞外表面；
- TAS1R3 的 CRD；
- TAS1R2/TAS1R3 二聚体界面附近；
- 个别蛋白可能同时接触 TAS1R2 和 TAS1R3。

## 2.3 Brazzein 的受体结合

Brazzein 是研究最深入的小型甜味蛋白之一。

早期建模和突变数据提示 brazzein 主要与 **T1R2** 发生接触，同时与 **T1R3** 有辅助作用；2006 年 J. Agric. Food Chem. 研究提出 brazzein 与受体的结合取向能解释多数突变结果。2010 年 J. Mol. Biol. 研究对 brazzein 和 T1R2/T1R3 进行突变分析，提出 brazzein 与受体存在多点结合。

典型实验包括：

- brazzein 表面残基突变；
- 人/鼠受体差异；
- 受体突变；
- HEK 细胞表达 hT1R2/hT1R3；
- Ca²⁺ 或 cAMP 信号检测；
- 甜味活性与突变位点关联。

对 AI 设计的意义：brazzein 分子小、结构稳定、受体结合突变资料较多，适合作为 RFdiffusion/ProteinMPNN 局部重设计和表面电荷优化模板。但它的难点是 4 对二硫键必须正确形成，且相关专利拥挤。

## 2.4 Thaumatin 的受体结合

Thaumatin 是大分子甜味蛋白，工业使用历史最长。研究显示 **T1R3 的 cysteine-rich domain, CRD** 对 thaumatin 的响应非常关键。2013 年 Biochimie 研究指出 hT1R3 CRD 中多个氨基酸残基参与 thaumatin 响应。Frontiers in Molecular Biosciences 2018 年研究进一步强调 thaumatin 表面正电荷对甜味活性有关键作用。

对 AI 设计的意义：thaumatin 的优势是法规和商业成熟、风味增强价值强，适合做复配中的后味修饰；短板是分子大、后甜长、多二硫键、结构改造和生产成本较高。

## 2.5 Monellin 的受体结合

Monellin 来自 serendipity berry，天然为双链蛋白。工业和 AI 设计通常使用单链化版本，例如 MNEI 或 single-chain monellin。

天然 monellin 由 A/B 两条链组成，热稳定性和加工稳定性有限。通过 linker 将其改为单链可以：

- 简化遗传表达；
- 降低链间解离风险；
- 改善稳定性；
- 为进一步突变提供骨架。

Monellin 同样被认为通过 T1R2/T1R3 的胞外表面和变构区域激活受体。近年来的 allosteric binding 研究将 monellin、brazzein、thaumatin 和 Honey Truffle active component 作为主要比较对象，强调这些蛋白序列和结构相差很大，但具有共同的正电荷表面特征和变构激活模式。

Monellin 是目前最适合 AI 改造的天然骨架之一：甜度高，单链版本已经存在，可通过计算稳定化提高加工适应性，新序列专利空间比 brazzein 更大，Amai Sweelin 已经提供商业先例。

## 2.6 Miraculin 的 pH 依赖机制

Miraculin 是典型味觉修饰蛋白。2011 年 PNAS 研究表明，miraculin 能够与 hT1R2/hT1R3 受体结合：

- 在中性 pH 下，它不激活或弱激活受体，甚至可以表现为拮抗/抑制其他甜味剂响应；
- 在酸性 pH 下，它转变为激动剂，激活甜味受体，使酸味食品产生甜味感。

这解释了神秘果“吃柠檬变甜”的现象。

对 AI 设计的意义：miraculin 提供了 pH 条件触发味觉开关的模板。这对酸性饮料、果汁、醋饮料、发酵乳制品可能有意义。但 miraculin 是糖蛋白，生产、糖型控制和法规更复杂。

## 2.7 Neoculin 和 Curculin 的 pH 依赖味觉修饰

Neoculin 和 curculin 都与酸味转甜有关。

2007 年研究显示 neoculin 可被 hT1R2/hT1R3 识别，并且 hT1R3 对其响应很重要。2008 年和 2015 年相关研究进一步显示，neoculin 的酸诱导甜味与 pH 依赖功能变化及 histidine 残基有关。

这类蛋白适合探索：

- 酸性食品专用甜味蛋白；
- pH-responsive protein sweeteners；
- 低糖酸饮料；
- 与柠檬酸、乳酸、苹果酸等体系协同。

但短期商业难度高于 monellin 和 brazzein。

## 2.8 研究甜味蛋白—受体结合的方法

### 1. 细胞受体实验

常用系统：

- HEK293/HEK293T 细胞；
- 共表达 hT1R2/hT1R3；
- 共表达 Gα16-gust44 或其他信号耦联蛋白；
- Ca²⁺ imaging；
- cAMP；
- IP1；
- 荧光/发光报告系统。

输出：EC50、Emax、剂量响应、pH 依赖、拮抗剂敏感性、人/鼠受体差异。

### 2. 受体突变和嵌合受体

通过人鼠 T1R2/T1R3 嵌合体、VFD/CRD/TMD 替换、单点突变和蛋白残基突变定位甜味蛋白作用区域。

### 3. 蛋白突变扫描

对 brazzein、thaumatin、monellin 进行 alanine scanning、charge reversal、loop mutation、disulfide disruption 和 stability mutation，观察甜味和受体活性变化。

### 4. 分子对接和分子动力学

用于提出结合模型，但不能单独证明甜味。

### 5. Cryo-EM 结构

2025 年已有全长人甜味受体 TAS1R2/TAS1R3 的 apo 和 sucralose-bound cryo-EM 结构发表。这对 AI 设计非常重要，因为过去甜味蛋白设计长期依赖同源模型，现在可以基于更接近真实受体的结构进行设计。

### 6. 人体感官实验

最终必须进行三角测试、描述性感官分析、蔗糖当量测定、time-intensity、后甜、苦味/涩味/金属味和食品基质测试。细胞实验和人体口感之间并不完全一致。

---

# 三、AI/计算设计甜味蛋白：现有案例

## 3.1 Amai Proteins：Sweelin

### 天然来源骨架

Sweelin 基于 **monellin**，即 serendipity berry 中的甜味蛋白。

### 改造目标

Amai 将其描述为通过 AI Computational Protein Design 设计的单链 monellin，目标包括：

- 提高稳定性；
- 改善工业食品加工兼容性；
- 保留强甜味；
- 降低成本；
- 支持精密发酵生产。

公开安全论文将其称为 DM31，是 AI-CPD 重新设计的 novel single-chain monellin。

### 生产

- 宿主：*Komagataella phaffii*；
- 生产形式：分泌表达；
- 下游：细胞去除、纯化、浓缩、干燥；
- FDA GRN 1269 对应一般食品甜味剂用途。

### 已做测试

公开安全论文和 GRAS 资料涉及：

- 基因毒性；
- 细菌回复突变；
- 哺乳动物微核；
- 90 天大鼠膳食毒性；
- 体外消化；
- 暴露评估；
- 生产菌株和杂质控制；
- 产品规格；
- 部分人体摄入或耐受数据。

### 局限

目前公开资料仍缺：完整设计过程、具体所有突变对甜度/稳定性的贡献、商业滴度、下游总回收率、真实终端产品长期销售数据和大规模消费者感官数据。

## 3.2 Oobli：改造型 monellin

FDA GRN 1183 对应 modified monellin produced by *K. phaffii* P-MON-040。

Oobli 的 monellin 说明 monellin 不只是 Amai 的路线，也可成为平台型甜味蛋白。其价值在于甜度高、口感相对干净、可与 brazzein 组成多蛋白产品矩阵，并且美国 GRAS 监管路径已被验证。

仍需关注的问题包括独立销量、真实食品应用场景、发酵滴度和纯化成本，以及与 brazzein 的应用分工。

## 3.3 计算稳定化单链 monellin

2024 年 Food Chemistry 发表的研究使用 PyRosetta ΔΔG 计算对 single-chain monellin 进行热稳定性改造，目标是获得 boiling-resistant monellin。

大致逻辑：

1. 选择 single-chain monellin 骨架；
2. 用 PyRosetta 计算突变对折叠自由能的影响；
3. 筛选可能提高稳定性的突变；
4. 构建突变体；
5. 表达和纯化；
6. 测定热稳定性和甜味保留。

这是非常典型的“AI/计算设计真正有用”的方向：不一定先追求更甜，而是先解决食品加工稳定性，同时保留甜味。

## 3.4 De novo TAS1R2 binder 设计

2026 年 arXiv 预印本报道了 **De novo design of protein binders targeting the human sweet taste receptor as potential sweet proteins**。

该工作流程包括：

- RFdiffusion：生成蛋白骨架；
- ProteinMPNN：设计序列；
- Boltz-1：结构预测和过滤；
- MM/GBSA：结合能评估；
- 靶点：TAS1R2 的 VFD 和 CRD。

该研究提出若干计算上可能结合 TAS1R2 的 binder，其中部分显示类似 brazzein 的结构合理性或较强预测结合能。

关键限制：这是计算框架探索，不等于已经开发出食品级甜味蛋白。仍缺少蛋白表达、纯化、折叠确认、T1R2/T1R3 细胞激活、人体感官、毒理、发酵放大和监管资料。

因此，de novo 设计可以作为第二代研发方向，但第一代商业产品不应完全依赖 de novo binder。

## 3.5 Zukora / Honey Truffle Sweet Protein

公开资料更强调其为蜜块菌来源的天然甜味蛋白并通过发酵生产，而不是明确的 AI 从头设计蛋白。

它提示行业并不只有传统八种甜味蛋白。真菌来源甜味蛋白可能成为新骨架来源。

MycoTechnology 宣布其完成自我 GRAS、已向 FDA 递交材料，并开始商业批次供应。但这与 FDA no-questions letter 不是同一状态。

## 3.6 百斯杰 Mellia Brazzein

FDA GRN 1207 文件主要描述的是由工程米曲霉生产的 brazzein-53 类型产品。百斯杰有 AI 辅助蛋白工程平台和 brazzein 突变体专利，但不能把所有专利突变体等同于当前 GRAS 产品。

Mellia 的重点不是“AI 从头设计”，而是 brazzein 天然骨架、工程米曲霉生产、高纯度规格、美国 GRAS 和工业发酵企业背景。对 AI 项目而言，它是很好的竞品和监管参考。

---

# 四、尚未商业化但值得关注的研究方向

## 4.1 Mabinlin

Mabinlin II 来自中国植物 *Capparis masaikai* 种子。其晶体结构显示为 A/B 两链并由二硫键连接，具有独特 all-alpha fold。Mabinlin II 具有较强热稳定性。

尚未商业化的原因包括：甜度不如 brazzein/monellin/thaumatin，重组表达和规模生产资料有限，食品安全和监管资料不足，商业需求不明确。

AI 价值：可作为耐热骨架研究对象，尤其适合探索小型二硫键稳定蛋白、热稳定甜味蛋白和酸性或高温食品应用。

## 4.2 Pentadin

Pentadin 同样来源于 *Pentadiplandra brazzeana*，1980s 被分离报道，甜度约数百倍于蔗糖。

主要问题是结构和序列资料少、生产体系不成熟、与 brazzein 同源植物但研究热度远低，并且没有主流监管或商业化记录。

短期不适合作为商业产品，但可作为未知天然甜味蛋白挖掘方向。

## 4.3 Curculin

Curculin 来自 *Curculigo latifolia*，既有甜味，也有酸味转甜作用。

主要问题是亚基组装复杂、热稳定和表达问题、机制尚不如 miraculin/neoculin 清晰、食品监管资料不足。

AI 价值：适合做 pH-responsive taste modifier 研究，不适合作为第一代通用甜味剂。

## 4.4 Neoculin

Neoculin 是 *Curculigo latifolia* 的异源二聚体蛋白。研究表明它由 hT1R2/hT1R3 识别，hT1R3 对响应非常重要；酸诱导甜味与 histidine 残基和 pH 依赖功能转换有关。

如果目标产品是酸性饮料、果汁、发酵乳，可以研究 neoculin/miraculin 类“酸触发甜味蛋白”。但其生产和监管难度明显高于 monellin/brazzein。

## 4.5 Miraculin

2011 年 PNAS 研究明确显示 miraculin 在中性 pH 下不作为普通甜味激动剂，在酸性条件下激活 hT1R2/hT1R3。

神秘果粉和片剂已有消费市场，但这不同于高纯重组 miraculin 原料的大规模食品配料市场。

Miraculin 是 pH-switch 设计的理想概念模板，但其糖蛋白性质和生产复杂性使其不适合作为第一代项目。

---

# 五、一个成功 AI 甜味蛋白需要做哪些实验

## 5.1 计算设计阶段

目标是从数千到数万个候选中筛出可以表达、稳定、可能激活受体并具有安全潜力的序列。

必做内容：

1. **选择骨架**：monellin、brazzein、thaumatin、miraculin/neoculin 或 de novo binder。
2. **结构预测**：AlphaFold、Boltz、Rosetta、ESMFold。
3. **受体对接**：靶点包括 TAS1R2 VFD、TAS1R2 CRD、TAS1R3 CRD、TAS1R2/TAS1R3 界面。不能只看 binding energy，还要看接触位点是否符合已知突变数据。
4. **分子动力学**：检查复合体稳定性、关键盐桥和氢键、蛋白柔性。
5. **制造性预测**：溶解度、聚集、二硫键、分泌信号兼容性、蛋白酶切位点、氧化位点、脱酰胺位点、不必要糖基化位点。
6. **安全性预筛**：AllergenOnline、COMPARE、毒素数据库、消化稳定性预测、与已知过敏原的 80 aa/35% 和短肽规则比对。
7. **FTO 预筛**：序列专利、突变体专利、表达宿主、分泌信号、食品应用和复配方案。

## 5.2 小规模表达阶段

目标是确认 AI 序列不是只存在于计算里，而是能生产出正确折叠的蛋白。

建议并行表达系统：

- *K. phaffii*；
- *A. oryzae*；
- *E. coli* 周质表达或胞内表达；
- 无细胞表达用于早筛；
- 哺乳或昆虫系统仅作为结构确认，不适合食品工业主线。

检测：SDS-PAGE、Western blot、LC-MS intact mass、peptide mapping、SEC-HPLC、RP-HPLC、circular dichroism、DSF/Tm、二硫键 mapping、糖基化检测、内毒素和宿主蛋白初筛。

## 5.3 受体细胞实验

目标是证明候选蛋白真正激活人甜味受体。

推荐系统：

- HEK293T transient expression；
- stable hT1R2/hT1R3 cell line；
- Gα16-gust44 或合适耦联；
- Ca²⁺ imaging 或荧光/发光 reporter。

必做设计：

1. 空载细胞对照；
2. 只表达 T1R2 或 T1R3 的对照；
3. hT1R2/hT1R3 完整受体；
4. 鼠 T1R2/T1R3 或嵌合体；
5. lactisole 抑制验证；
6. 已知阳性对照：sucrose、sucralose、thaumatin、brazzein 或 monellin；
7. 蛋白热处理前后对比；
8. pH 梯度；
9. 剂量响应曲线。

输出：EC50、Emax、Hill coefficient、最大响应、与阳性对照相对活性、受体亚基依赖、pH 依赖、是否存在拮抗或协同。

## 5.4 人体感官实验

受体细胞实验不能完全代表口感。蛋白在口腔中的停留、黏度、唾液蛋白、香气和 pH 均会影响人体甜感。

第一轮感官：

- 小样本训练型 panel；
- 水体系；
- 与 2%、5%、8%、10% 蔗糖对照；
- 识别阈值；
- 等甜浓度；
- 苦味、涩味、金属味；
- 后甜。

第二轮感官：

- time-intensity；
- 真实饮料基质；
- 酸性饮料；
- 蛋白饮料；
- 乳制品；
- 与甜菊糖苷、罗汉果苷、阿洛酮糖复配。

第三轮消费者测试：盲测、偏好测试、购买意愿、标签认知、与现有代糖方案比较。

## 5.5 食品基质测试

### 饮料

重点测试 pH 2.5—7、巴氏杀菌、UHT、碳酸、茶多酚、金属离子、香精和货架期。

### 乳品/蛋白饮料

重点测试乳清/酪蛋白/植物蛋白相互作用、沉淀、粘度、热处理、蛋白酶残留、风味遮蔽。

### 巧克力和烘焙

不建议作为首发，但若测试，需要额外解决体积、糖的结构作用、美拉德反应、焦糖化、水分活度和质构。

## 5.6 发酵放大实验

### 放大路径

```text
24/96 深孔板
→ 50 mL shake flask
→ 1 L 发酵罐
→ 5–10 L
→ 30–100 L
→ 300–1000 L
→ 工程批
```

关键指标：滴度 g/L、胞外分泌比例、单体比例、正确二硫键比例、发酵周期、批次稳定性、蛋白酶降解、杂质谱、工艺窗口。

不建议只优化表达量。要同时看：

```text
effective sweetness titer
= protein titer × correct folding fraction × relative sweetness
```

## 5.7 下游纯化实验

必做：发酵液澄清、微滤、超滤/纳滤、离子交换、洗滤、浓缩、干燥。

评价指标：总回收率、纯度、宿主蛋白、残留 DNA、树脂负载、树脂循环寿命、膜通量、膜污染、产物损失、每公斤成本。

目标：食品配料不应采用过度生物药化的工艺。目标应是：

```text
一次捕获 + 一次抛光 + 膜洗滤 + 喷雾干燥
```

## 5.8 稳定性实验

### 纯蛋白

- Tm；
- DSC；
- DSF；
- CD；
- freeze-thaw；
- 25/37/40°C 加速；
- 光照；
- 氧化；
- 金属离子；
- pH 2—8。

### 食品中

- 巴氏杀菌后甜度保留；
- UHT 后甜度保留；
- 3/6/12个月货架期；
- 香精相互作用；
- 颜色变化；
- 浑浊和沉淀；
- 微生物稳定。

## 5.9 安全性实验

### 计算和体外

- 过敏原同源性；
- 毒素同源性；
- 模拟胃液消化；
- 模拟肠液消化；
- 热降解产物；
- Ames test；
- mammalian micronucleus；
- 细胞毒性。

### 动物

- 14天或28天探索；
- 90天重复经口毒性；
- NOAEL；
- 血液、生化、病理；
- 剂量选择基于暴露评估。

### 人体

可选但有价值：小规模耐受性、血糖/胰岛素短期影响、胃肠道耐受、感官和摄入接受度。

注意：这些不能宣传为治疗糖尿病或减肥功效，除非另有临床试验证据和合规路径。

## 5.10 监管前资料包

成熟候选需要形成：完整序列、生产菌株、遗传构建、工艺流程、五批次以上成分数据、产品规格、杂质控制、残留 DNA 和宿主蛋白、稳定性、食品用途、最大使用量、暴露评估、毒理、过敏原、标签建议和 FTO 分析。

---

# 六、研发路线建议

## 6.1 第一代产品路线

推荐：

```text
single-chain monellin 或 brazzein-53
→ AI 局部改造
→ K. phaffii / A. oryzae 双宿主筛选
→ 饮料场景验证
→ 美国 GRAS 或中国新品种路径
```

不推荐第一代直接做：

- 完全 de novo；
- miraculin 类糖蛋白；
- 巧克力/烘焙专用蛋白；
- 复杂多亚基 neoculin/curculin。

## 6.2 设计目标排序

优先级从高到低：

1. 能表达；
2. 能正确折叠；
3. 能分泌；
4. 能激活人 T1R2/T1R3；
5. 甜味可被人体感知；
6. 后甜和异味可接受；
7. 食品加工稳定；
8. 纯化成本可控；
9. 安全性无明显问题；
10. 有专利和商业空间。

不要把“dock 分数最高”作为第一目标。

## 6.3 推荐项目里程碑

### 0—3个月

- 文献和专利图谱；
- 选择 2 个骨架；
- 建立受体结构模型；
- 第一批计算候选。

### 3—6个月

- 合成 100—300 个候选；
- 小规模表达；
- 初步结构和稳定性筛选；
- 受体细胞实验建立。

### 6—12个月

- 筛出 5—20 个候选；
- 纯化；
- 人体小样本感官；
- 饮料基质测试；
- 初步发酵放大。

### 12—18个月

- 1—3 个 lead；
- 中试发酵；
- 下游工艺；
- 稳定性；
- 初步安全资料；
- FTO 完成。

### 18—30个月

- 冻结序列；
- 毒理；
- GRAS/新食品添加剂资料；
- 客户中试；
- 生产工艺锁定。

---

# 七、重点文献和资料清单

## 7.1 总论和受体机制

1. Zhao X. et al. 2021. **Protein Sector and Its Role for Sweet Properties.** https://pmc.ncbi.nlm.nih.gov/articles/PMC8249704/
2. Temussi P.A. 2002. **Why are sweet proteins sweet? Interaction of brazzein, monellin and thaumatin with the T1R2–T1R3 receptor.** https://pubmed.ncbi.nlm.nih.gov/12208493/
3. Tancredi T. et al. 2004. **Interaction of sweet proteins with their receptor.** https://pubmed.ncbi.nlm.nih.gov/15153113/
4. Treesukosol Y. et al. 2011. **The Functional Role of the T1R Family of Receptors in Sweet Taste and Feeding.** https://pmc.ncbi.nlm.nih.gov/articles/PMC3186843/
5. Shi Z. et al. 2025. **Structural and functional characterization of human sweet taste receptor.** https://pubmed.ncbi.nlm.nih.gov/40555359/
6. Juen Z. et al. 2025. **The structure of human sweetness.** https://www.cell.com/cell/fulltext/S0092-8674(25)00456-8
7. Wang H. et al. 2025. **Structure and activation mechanism of human sweet taste receptor.** https://www.nature.com/articles/s41422-025-01156-x
8. Vo P. et al. 2026. **Sweet Protein Allosteric Binding and Activation of the Human T1R2/R3 Sweet Taste Receptor.** https://pubmed.ncbi.nlm.nih.gov/41591896/

## 7.2 Brazzein

9. Assadi-Porter F.M. et al. 2010. **Key amino acid residues involved in multi-point binding interactions between brazzein and the T1R2–T1R3 human sweet receptor.** https://pmc.ncbi.nlm.nih.gov/articles/PMC2879441/
10. Eric W.D. et al. 2006. **Interactions of the Sweet Protein Brazzein with the Sweet Taste Receptor.** https://pmc.ncbi.nlm.nih.gov/articles/PMC2527743/
11. Novik T.S. et al. 2023. **Sweet-Tasting Natural Proteins Brazzein and Monellin: Safety Assessment.** https://www.mdpi.com/2304-8158/12/22/4065
12. Lynch B. et al. 2023. **Safety evaluation of oubli fruit sweet protein (brazzein) derived from Komagataella phaffii.** https://journals.sagepub.com/doi/abs/10.1177/23978473231151258
13. FDA GRN 1142. **Brazzein produced by Komagataella phaffii. Oobli.** https://www.cfsanappsexternal.fda.gov/scripts/fdcc/?id=1142&set=GRASNotices
14. FDA GRN 1207. **Brazzein preparation produced by Aspergillus oryzae. Nanjing Bestzyme.** https://www.hfpappexternal.fda.gov/scripts/fdcc/index.cfm?id=1207&set=grasnotices

## 7.3 Monellin / Sweelin

15. Liu Y. et al. 2024. **Computational design towards a boiling-resistant single-chain sweet protein monellin.** https://pubmed.ncbi.nlm.nih.gov/38159314/
16. Lifshitz Y. et al. 2025. **Safety Evaluation of Serendipity Berry Sweet Protein From Komagataella phaffii.** https://pubmed.ncbi.nlm.nih.gov/40159929/
17. Freeman E.L. et al. 2024. **Comprehensive safety assessment of serendipity berry sweet protein produced from Komagataella phaffii.** https://pubmed.ncbi.nlm.nih.gov/38190935/
18. FDA GRN 1183. **Modified monellin produced by Komagataella phaffii P-MON-040. Oobli.** https://www.hfpappexternal.fda.gov/scripts/fdcc/index.cfm?id=1183&set=GRASNotices
19. FDA GRN 1269. **Modified monellin / Sweelin produced by Komagataella phaffii CBS 150005. Amai Proteins.** https://www.hfpappexternal.fda.gov/scripts/fdcc/index.cfm?id=1269&set=GRASNotices

## 7.4 Thaumatin

20. Masuda T. et al. 2013. **Five amino acid residues in cysteine-rich domain of human T1R3 were involved in the response for sweet-tasting protein thaumatin.** https://pubmed.ncbi.nlm.nih.gov/23370115/
21. Masuda T. et al. 2018. **Positive Charges on the Surface of Thaumatin Are Crucial for the Multi-Point Interaction with the Sweet Taste Receptor.** https://www.frontiersin.org/articles/10.3389/fmolb.2018.00010/full
22. Ide N. et al. 2009. **Interactions of the Sweet-Tasting Proteins Thaumatin and Lysozyme with the Human Sweet-Taste Receptor.** https://pubs.acs.org/doi/10.1021/jf803956f

## 7.5 Miraculin / Neoculin / Curculin

23. Koizumi A. et al. 2011. **Human sweet taste receptor mediates acid-induced sweetness of miraculin.** https://pmc.ncbi.nlm.nih.gov/articles/PMC3189030/
24. Koizumi A. et al. 2007. **Taste-modifying sweet protein, neoculin, is received at human T1R2-T1R3.** https://cir.nii.ac.jp/crid/1363107368242093952
25. Nakajima K. et al. 2008. **Acid-induced sweetness of neoculin is ascribed to its pH-dependent agonistic-antagonistic interaction with human sweet taste receptor.** https://faseb.onlinelibrary.wiley.com/doi/pdf/10.1096/fj.07-100289
26. Koizumi T. et al. 2015. **Identification of key neoculin residues responsible for the binding and activation of the human sweet taste receptor.** https://www.nature.com/articles/srep12947
27. Curculin Exhibits Sweet-tasting and Taste-modifying Activities through different modes of interaction with T1R2-T1R3. https://www.semanticscholar.org/paper/0a436f381afd6322bf0081594ccaceaa5cb35d24

## 7.6 Mabinlin / Pentadin

28. Li D.F. et al. 2008. **Crystal structure of Mabinlin II: A novel structural type of sweet proteins and the main structural basis for its sweetness.** https://pubmed.ncbi.nlm.nih.gov/18308584/
29. RCSB PDB 2DS2. **Crystal structure of Mabinlin II.** https://www.rcsb.org/structure/2ds2
30. Kant R. 2005. **Sweet proteins – Potential replacement for artificial low calorie sweeteners.** https://pmc.ncbi.nlm.nih.gov/articles/PMC549512/
31. Isolation and characterization of pentadin, the sweet principle of *Pentadiplandra brazzeana*. https://www.researchgate.net/publication/31002804_Isolation_and_characterization_of_Pentadin_the_sweet_principle_of_Pentadiplandra_brazzeana_Baillon

## 7.7 De novo / AI 蛋白设计

32. Ding S., Zhang Y. 2026. **De novo design of protein binders targeting the human sweet taste receptor as potential sweet proteins.** https://arxiv.org/abs/2601.14574
33. RFdiffusion. **Diffusion model for protein backbone generation.** https://www.nature.com/articles/s41586-023-06415-8
34. ProteinMPNN. **Robust deep learning-based protein sequence design using ProteinMPNN.** https://www.science.org/doi/10.1126/science.add2187
35. Boltz-1. **Biomolecular interaction modeling / structure prediction framework.** https://github.com/jwohlwend/boltz

---

# 八、最终建议

如果目标是做“AI 甜味蛋白”项目，建议按以下策略推进：

1. **第一代产品不要做完全 de novo。** 优先使用 single-chain monellin 或 brazzein-53 作为骨架。
2. **把 AI 设计目标从“更甜”扩展到“能生产、能纯化、能稳定、口感好”。** 甜度只是一个指标，发酵滴度和后甜同样重要。
3. **先做饮料应用，不要一开始做烘焙和巧克力。** 饮料主要需要甜味信号，最容易验证。
4. **建立人 T1R2/T1R3 细胞实验平台。** 这是 AI 候选从计算走向实验的第一道功能关口。
5. **必须做人体感官 time-intensity。** 没有感官数据，不能判断一个甜味蛋白是否真正有商业价值。
6. **发酵工艺要与序列设计同步。** 不能先设计出一个“理论很甜”的蛋白，再发现宿主不表达或下游无法纯化。
7. **尽早做专利和监管边界分析。** Brazzein 和 monellin 领域已有大量序列、突变、生产和应用专利。
8. **第二代可以布局 pH-responsive 或 de novo。** Miraculin/neoculin 类蛋白和 de novo TAS1R2 binder 有前沿价值，但短期商业风险高。

最终，一个成功的 AI 甜味蛋白不是“模型生成的序列”，而是能够完成以下闭环的产品：

```text
天然或人工骨架
→ 可解释的受体作用机制
→ 可重复表达和正确折叠
→ 人 T1R2/T1R3 激活
→ 人体甜味确认
→ 真实食品中口感优于现有方案
→ 发酵和下游成本可接受
→ 安全资料完整
→ 监管可通过
→ 食品企业愿意持续采购
```
