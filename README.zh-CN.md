[English](README.md) | [中文](README.zh-CN.md)

# BDA Workbench

**[Bigo](https://bigo.bio) 生物材料设计自动化（BDA）平台软件**

> *EDA 让芯片可编程，Bigo 让生物材料可编程。*

BDA Workbench 是比构生物 **BDA+** 平台的工程实现——一套设计自动化系统，将蛋白质和生物材料的功能需求转化为可审计、可实验验证的工程任务。本仓库包含全栈工作台：项目空间、工作流编排、候选评估、湿实验反馈与交付打包。

---

## 为什么需要 BDA+

生物材料设计仍处于碎片化阶段。一个 binder 或展示平台任务往往被拆成 3～5 个外包节点——设计、结构评估、表达纯化、BLI/SPR、功能验证——却没有单一责任主体对最终结果负责。失败难以归因，阴性数据很少回流到下一轮设计，项目结束时留下的多是报告，而非可复用资产。

**BDA** 解决「如何设计」：需求输入、路线选择、候选生成、风险评分和版本记录，统一在同一套流程中。

**BDA+** 在此基础上解决「如何验证、如何复盘、如何进入下一轮设计」：湿实验读出、结构化失败归因，以及驱动下一轮候选排序的闭环反馈引擎。

| 维度 | 传统分散路径 | BDA+ 目标路径 |
|------|-------------|--------------|
| 责任主体 | 设计、表达、检测分散在多家供应商 | 从任务定义到验证与下一轮建议，单一项目责任边界 |
| 决策方式 | 依赖专家经验与多供应商协调 | 任务规格、路线选择、候选排序与实验记录进入统一项目档案 |
| 失败处理 | 表达或结合失败后常需重新拆任务 | 失败样本与实验条件进入 Feedback Engine，影响下一轮排序 |
| 数据资产 | 项目结束留下报告，阴性数据难复用 | 成功与失败数据结构化沉淀，逐步变成跨任务模板 |

---

## 平台模块

BDA+ 由六个工程模块组成。本工作台为每个模块提供软件层实现：

| 模块 | 在 BDA+ 中的角色 | 在本仓库中 |
|------|-----------------|-----------|
| **Target & Product Definition**（靶点与产品定义） | 定义靶点、抗原、催化位点、稳定性、表达要求与 TPP 约束 | 项目创建、靶点画像、轮次简报 |
| **Candidate Design Engine**（候选设计引擎） | 在任务约束下生成候选 | 工作流画布与模型插件（RFdiffusion、ProteinMPNN 等） |
| **Evaluation Gate**（评估闸门） | 湿实验前过滤高风险候选 | BDA 评分过滤器、结构/功能联合排序 |
| **Wet Lab Validation**（湿实验验证） | 表达、纯化、BLI/SPR、酶活、组装验证 | 结果视图、实验上传、验证指标 |
| **Data & Experiment Operations**（数据与实验运营） | 版本记录、实验条件、候选标签、项目决策 | SQLite/PostgreSQL 模式、审计日志、制品存储 |
| **Closed-Loop Optimization**（闭环优化） | 成功/失败样本驱动下一轮设计 | 第二轮重设计约束、Copilot 解释、反馈闭环 |

---

## 应用范围

BDA+ 在共享设计引擎上支持两类应用模式：

- **功能驱动** — 从头设计蛋白药物、胞内或膜蛋白 binder、工业酶。交付物为结合、抑制或催化功能。近期验证案例包括 PPI binder（如 BP326）、CD3 结合蛋白、核黄素酶（RibH）结合蛋白。
- **结构驱动** — 抗原展示、功能蛋白展示、蛋白质晶体、可响应纳米笼。交付物为可控的构象、密度、几何与递送属性。

当前 MVP 以 PD-1 案例演示 **binder** 工作流。展示平台与工业酶 PoC 路径共用同一套 BDA 语法，仅输入约束与验收指标不同。

---

## 当前 MVP：PD-1 Binder 演示

种子项目 `proj_pd1_0423` 演示完整的设计–验证–迭代闭环：

1. **定义** PD-1 binder 项目与靶点画像。
2. **规划** 工作流路线：RFdiffusion → ProteinMPNN → AlphaFold2 → Rosetta → BDA 过滤器 → 湿实验验证。
3. **排序** 候选并解释 `PD1Binder_c4361` 为何锚定下一轮。
4. **验证** BLI/SEC 证据、交付包内容与第二轮重设计约束。

### 界面视图

| 路由 | 用途 |
|------|------|
| `/experiments` | 项目入口、概览卡片、Agent 工作区 |
| `/workflow` | React Flow 画布、模型插件、计算状态、Copilot |
| `/candidates` | 排序表格、过滤器、Mol\* 结构查看器、解释说明 |
| `/results` | 验证指标、实验上传、交付 ZIP、第二轮简报 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | React 19、TypeScript、Vite、Tailwind CSS 4、TanStack Query/Table、Zustand、React Router、React Flow、Mol\*、Zod |
| **后端** | FastAPI、Pydantic、Uvicorn、structlog |
| **数据库** | SQLite（本地 MVP）；可通过 `BDA_DB_PATH` 切换 PostgreSQL |
| **异步任务** | Celery + Redis |
| **对象存储** | 本地文件系统或 MinIO |
| **计算** | Docker 模型插件：ProteinMPNN、RFdiffusion、AlphaFold2、Rosetta |
| **认证** | JWT + RBAC（admin / researcher / viewer） |
| **Copilot** | 规则引擎演示；可选 OpenAI 兼容 LLM |
| **部署** | Docker Compose、nginx、Prometheus、Grafana |

---

## 快速开始

### 环境要求

- Python 3.13
- Node.js 22
- npm

### 本地开发

```sh
# 初始化数据库并写入演示数据
python3 backend/scripts/init_db.py
python3 backend/tests/check_db.py

# 同时启动后端与前端
chmod +x scripts/dev.sh
./scripts/dev.sh
```

或分别启动各服务：

```sh
python3 -m pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 127.0.0.1 --port 8100 --reload
```

```sh
cd frontend
npm install
npm run dev
```

打开 **http://127.0.0.1:5173?project=proj_pd1_0423**（API 运行在 `8100` 端口，经 Vite 代理）。

### Docker Compose（类生产环境）

```sh
cp .env.example .env
docker compose up -d
```

| 服务 | 端口 | 角色 |
|------|------|------|
| `nginx` | 8080 | 统一入口 |
| `api` | 8100 | FastAPI 后端 |
| `frontend` | 5173 | 构建后的 SPA |
| `worker` | — | Celery 计算 Worker |
| `redis` | 6379 | 任务队列 / 缓存 |
| `minio` | 9000 / 9001 | 制品存储 |
| `postgres` | 5432 | 可选 PostgreSQL |
| `prometheus` | 9090 | 指标采集 |
| `grafana` | 3000 | 监控面板 |

Docker 默认管理员账号：`admin` / `admin123`

将 `BDA_COMPUTE_MODE=docker` 设为 `docker`，可向真实模型插件容器提交任务（默认为 `demo` 演示模式）。

---

## 配置

复制 `.env.example` 为 `.env`。主要变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BDA_DB_PATH` | `backend/db/bda.sqlite3` | SQLite 路径或 PostgreSQL URL |
| `BDA_COMPUTE_MODE` | `demo` | `demo`（阻塞任务）或 `docker`（真实容器） |
| `BDA_ARTIFACTS_BACKEND` | `local` | `local` 或 MinIO 存储 |
| `BDA_JWT_SECRET` | — | JWT 签名密钥（生产环境请修改） |
| `VITE_API_BASE` | `/api/v1` | 前端 API 基址（构建时注入） |
| `LLM_API_BASE` / `LLM_API_KEY` | — | 可选 Copilot LLM 提供商 |

API 文档：**http://127.0.0.1:8100/api/docs**

---

## 仓库结构

```
BDA/
├── docs/                  # 产品需求、架构说明、验收清单
├── frontend/              # React SPA（实验、工作流、候选、结果）
├── backend/               # FastAPI 网关、数据库模式、Copilot、计算适配器
├── docker/models/         # 模型插件容器镜像
├── alembic/               # PostgreSQL 迁移
├── nginx/                 # 反向代理配置
├── monitoring/            # Prometheus 配置
├── scripts/dev.sh         # 一键本地开发
└── fig/                   # 演示视觉素材
```

### 文档

| 文档 | 说明 |
|------|------|
| [`docs/PRD01_完整产品需求文档.md`](docs/PRD01_完整产品需求文档.md) | 完整产品需求（愿景、用户、路线图） |
| [`docs/FRD01_前端设计说明.md`](docs/FRD01_前端设计说明.md) | 前端设计规范与验收标准 |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 系统架构、API 分组、部署说明 |
| [`docs/PHASE1_ACCEPTANCE.md`](docs/PHASE1_ACCEPTANCE.md) | Phase 1 + P1 验收清单 |

---

## 测试

```sh
python3 -m pytest backend/tests/test_api.py -q
cd frontend && npm test
```

推送时 GitHub Actions（`.github/workflows/ci.yml`）会自动运行两套测试。

---

## 路线图

| 阶段 | 状态 | 范围 |
|------|------|------|
| **Phase 1 + P1** | 已完成 | PD-1 演示闭环、工作流画布、候选排序、结果/交付、认证、Copilot 规则、Docker 脚手架 |
| **Phase 2** | 规划中 | 真实 GPU Worker、完整 LLM Copilot、多租户部署、跨任务模板 |

---

## 关于 Bigo

**Bigo（比构生物）** 正在构建可编程生物材料的设计自动化基础设施。团队源自 David Baker 蛋白质设计体系，商业化的是客户可采购、可验收的交付系统，而非单篇论文或单一模型。

近期重点：面向药企早研团队的 **平台项目交付**，从 binder 任务切入，延伸至展示平台与工业酶 PoC。客户在同一项目责任边界内获得候选包——序列、结构、表达数据、BLI/SPR 读出、版本记录与下一轮建议。

**联系：** [contact@bigo.bio](mailto:contact@bigo.bio) · [bigo.bio](https://bigo.bio)

---

## 许可

专有软件。© Bigo Biotech. 保留所有权利。
