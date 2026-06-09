---
name: stock-analysis
description: 全自动股票基本面分析。当用户要求分析某只股票、评估投资价值、想"读懂"一家公司时触发。接受港股代码(XX.HK)、美股代码(XX.US)、A股代码(XX.SH/.SZ)或中英文公司名。即使用户只说"分析一下腾讯"或"帮我看看名创优品"也应触发。不用于纯股价查询、宏观分析或行业整体研究。
---

# 读懂股票 — 全自动基本面分析 Skill

> **⚠️ 核心规则：** 依照 `references/stock_analysis_framework.md` 搭建的股票分析框架完成股票分析。
> 报告的**结构和内容要求**不在本文件中，而在 `references/stock_analysis_framework.md`。
> **你必须先完整阅读框架文件，再开始任何数据采集。框架文件是本 skill 执行的唯一模板依据。**
>
> **申报文件下载指南：** `references/filing_download_guide.md` 包含各市场（美股/港股/A股）原始公司文件的下载命令。
> **信息提取指南：** `references/critical_data_extraction.md` 定义从原始文件中提取什么信息到 `critical_data.md`。

---

## 工作流程总览

```
Phase 0: 先读框架文件 → 理解9步结构
    ↓
Phase 1: 解析标的 → 建立 <股票名称> 分析文件夹
    ↓
Phase 2: 数据采集
    ├─ 第1层：Longbridge 原生命令（collect_data.sh，含财务/行情/新闻/社区）← 主力
    ├─ 第2a层：申报文件原文下载（年报/季报/电话会等）→ source_docs/
    ├─ 第2b层：信息提取 → critical_data.md
    └─ 补充层：WebSearch（仅数据缺失时使用）
    ↓
Phase 3: 按照框架撰写报告 → 保存 report.md + critical_data.md
    ↓
Phase 4: 质量检查 → 确认分析完整性
结束：stock-analysis/<股票名称>/ 包含 report.md + critical_data.md + source_docs/
```

---

## Phase 0：理解分析框架

阅读 `references/stock_analysis_framework.md` 文件，确认股票分析方法，后续分析严格按照该框架执行。

---

## Phase 1：解析标的

用户输入可能是：

| 输入类型 | 例子 | 处理方式 |
|---------|------|---------|
| **标准代码** | `MNSO.US`、`9896.HK`、`600519.SH`、`300750.SZ` | 直接使用 |
| **英文名** | `MINISO`、`Tencent`、`Nike` | WebSearch 查代码 |
| **中文名** | `名创优品`、`腾讯`、`贵州茅台` | WebSearch 查代码 |
| **模糊描述** | `那个做盲盒的公司` | AskUserQuestion 确认 |

**代码解析方法：**
- 搜索词：`"<公司名> 股票代码"` 或 `"<company name> stock ticker"`
- 多地上市：优先用 Longbridge 支持的、流动性好的那个市场（HK > US > SH/SZ）
- 记录多个代码备用
- 解析失败 → AskUserQuestion 确认

**解析完成后，记录市场类型**（US / HK / SH / SZ），后续文件获取路径依赖这个判断。

### 建立分析文件夹

解析出股票代码后，通过 `longbridge company` 获取公司中文名，再用公司名创建文件夹：

```bash
# 获取公司中文名（Name栏）
longbridge company <CODE>

# 用脚本创建文件夹
bash scripts/setup_dir.sh "<股票名称>"
```

**文件夹结构说明：**
```
stock-analysis/
  └── <股票名称>/                     # 以公司中文名命名（来自 longbridge company）
      ├── report.md                  # 最终分析报告
      ├── critical_data.md           # 关键信息提取表（从各文件提取的结构化数据）
      └── source_docs/               # 一手原始文档（文件名含发布时间YYYYMMDD）
          ├── 年报_20260409.txt        # 美股：SEC EDGAR 10-K全文
          ├── 季报_20260502.txt        # 美股：SEC EDGAR 10-Q全文
          ├── 委托书_20260409.txt      # 美股：SEC EDGAR DEF 14A全文
          ├── 内部人交易.txt          # 美股：Form 4内部人交易
          ├── 电话会纪要.md           # 电话会Q&A
```

---

## Phase 2：数据采集

### 设计原则

**Longbridge 能直接拿到的数据，一律不用 WebSearch。**
**每一层的数据采集命令，都标注了它服务框架的哪个 Step。** 你在采集时就知道数据用来回答什么。

### 第1层：Longbridge 原生命令（🟢 高可靠）

直接调用 `scripts/collect_data.sh` 即可一键采集所有模块，数据保存在stock-analysis/<名称>/data目录下。各模块与框架步骤的对应关系见下表。

```bash
# 一键采集所有 Longbridge 数据
bash scripts/collect_data.sh <SYMBOL> "stock-analysis/<股票名称>/"
```

**数据-框架映射表：**

| 模块 | 数据 | 服务于框架 |
|------|------|-----------|
| A 行情与价格 | quote、kline | Step 7 估值 |
| B 财务报表 | 利润表(IS)、资产负债表(BS)、现金流量表(CF) | Step 1 生意本质、Step 4 财务质量 |
| C 估值指标 | calc-index、valuation、consensus | Step 7 估值 |
| D 公司治理 | company、executive、shareholder、dividend | Step 1 生意本质、Step 5 股东回报与治理 |
| E 机构评级 | institution-rating、industry-valuation | Step 7 估值 |
| F 股东结构 | shareholder（美股+港股）、insider-trades（仅美股） | Step 5 治理 |
| G 内部人交易 | insider-trades（仅美股） | Step 5 治理 |
| H 新闻与社区 | news（标题+摘要）、topic（社区讨论） | Step 5 治理、Step 6 宏观 |

### 第2a层：申报文件原文下载（🟢 高可靠）

阅读 `references/filing_download_guide.md` 文件，了解各市场原始文件的下载命令，读取完成后再继续以下步骤。

按照下面的文件清单依次下载文件，**不可跳过任何一个文件，即使优先级为低。**
**关键：年报和季报均无法获取 → 停止分析**，告知用户无法继续。

| # | 文件 | 优先级 | 说明 |
|---|------|--------|------|
| 1 | 年报 | 🔴 必选 | **中概股（BABA/JD/MNSO 等）用 20-F 而非 10-K** |
| 2 | 季报/中报 | 🔴 必选 |  |
| 3 | 财报电话会 Q&A | 🔵 高 |  |
| 4 | 招股书（上市5年内） | 🔵 高 |  |
| 5 | 同行公司年报 | 🟡 中 |  |
| 6 | 行业研究报告 | 🟡 中 |  |
| 7 | 宏观与政策 | ⚪ 低 |  |

### 第2b层：信息提取到 critical_data.md（🟢 高可靠）

阅读 `references/critical_data_extraction.md` 文件，了解各文件的信息提取要求，读取完成后再继续以下步骤。

**按照提取指南，逐一处理 source_docs/ 中已下载的文件，将关键信息提取到 `critical_data.md`：**

1. 按节号对照表（第一节→年报、第二节→季报、第三节→电话会……）组织内容
2. 每条信息按格式规范记录：信息主题、来源、服务于、原文摘录
3. 不做分析、不解读、不下结论——仅摘录原文关键段落和数字

---

## Phase 3：报告生成

**报告的 9 步结构由 `references/stock_analysis_framework.md` 完整定义，唯一模板依据是那个文件。** 

** 核心要求 **
1. 写报告前重读框架文件，确保理解每一 Step 的核心问题。
2. 报告的信息源包括data、source_docs目录下的文件，重点关注critical_data.md摘录的关键信息，整理各 Step 问题答案，每个问题的答案都必须有依据，不可胡编乱造
3. 框架文件中每个 Step 下方的所有问题，**都必须逐一回答**，要求有理有据。回答句式完整，可读性强。

注意项：
**Step 0（公司类型判断）** 是整个分析的元决策——从框架分类表中找出最匹配的类型，锁定行业核心 KPI，填写行业指标表。
**Step 3 竞争优势的真实性检验** 区分管理层说法与财报验证——年报/电话会里说的是"声称"，毛利率/ROIC/复购率才是"验证"，不把管理层说的当成事实
**Step 9 持仓管理规则：** 默认不输出。仅当用户明确问"该不该买"/"仓位多少"/"什么时候卖"等持仓问题时输出，且末尾附加免责声明。

其他：
**报告开头声明模板：**
```
## 数据获取声明
| 数据来源 | 状态 | 说明 |
|---------|------|------|
| 财务数据（Longbridge直连） | ✅ 已获取 | FY20XX-FY20XX 三表完整 |
| 年报原文 MD&A | ✅/❌ | — |
| 招股书行业概述 | ✅/❌ | — |
| 财报电话会 Q&A | ✅/❌ | — |
| 行业研报 | ✅/❌ | — |
```

**格式：** 简体中文，金额单位统一用亿（人民币 RMB，美元 $）。

报告完成后保存到 `stock-analysis/<股票名称>/report.md`。

---

## Phase 4：质量检查

依照 `references/quality_checklist.md` 逐项确认分析完整性后，输出最终文件夹结构：

```
📁 分析结果已保存到 stock-analysis/<股票名称>/
   ├── report.md               ← 完整分析报告
   ├── critical_data.md        ← 关键信息提取表
   └── source_docs/            ← 一手原始文档
```

---

## 代码解析参考（常用公司对照表）

| 中文名 | 港股 | 美股 | A股 |
|--------|------|------|-----|
| 腾讯 | 700.HK | TCEHY.US | — |
| 阿里巴巴 | 9988.HK | BABA.US | — |
| 美团 | 3690.HK | — | — |
| 拼多多 | — | PDD.US | — |
| 小米 | 1810.HK | XIACY.US | — |
| 比亚迪 | 1211.HK | BYDDY.US | 002594.SZ |
| 茅台 | — | — | 600519.SH |
| 宁德时代 | — | — | 300750.SZ |
| 名创优品 | 9896.HK | MNSO.US | — |
| 泡泡玛特 | 9992.HK | — | — |
| 百度 | 9888.HK | BIDU.US | — |
| 京东 | 9618.HK | JD.US | — |
| 网易 | 9999.HK | NTES.US | — |
| 携程 | 9961.HK | TCOM.US | — |
