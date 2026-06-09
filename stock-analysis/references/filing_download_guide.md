# 各市场申报文件下载指南

> 仅包含各市场原始文件的**下载命令**。信息提取要求见 `references/critical_data_extraction.md`。
> 执行流程由 SKILL.md Phase 2 第 2a 层驱动，本文件按需查阅对应章节。

---

## 通用保存规范

- **保存位置：** `source_docs/`，文件名格式 `类型_公司名称_YYYYMMDD.txt`（如 `年报_中际旭创_20260409.txt`）
- **保存内容：** 一手原始文档全文
- **日期来源：** 美股从 SEC 头部 `CONFORMED PERIOD OF REPORT` 提取；港股从 `longbridge filing` 的 `publish_at` 列提取；A股从巨潮 API 返回的 `announcementDate` 字段提取（cninfo_download.py 自动处理）

---

## 一、年度报告

### Step 1：确定年报表格类型

根据市场判断使用的年报表格：

| 市场 | 表格类型 | 判断依据 |
|------|---------|---------|
| **美股·中概股** | 20-F | `longbridge company` 返回 `country: CN` 且市场为 US |
| **美股·非中概** | 10-K | 美国本土公司（country 非 CN） |
| **港股** | 年报 PDF | — |
| **A股** | 年报 PDF | — |

### Step 2：下载年报

**美股（10-K 或 20-F）：**
```
# 中概股（BABA/JD/BIDU/MNSO/PDD/NTES/TCOM 等）
python3 scripts/sec_filing.py <TICKER> --name "<公司名>" 20-F -o "stock-analysis/<名称>/source_docs/"

# 非中概美股
python3 scripts/sec_filing.py <TICKER> --name "<公司名>" 10-K -o "stock-analysis/<名称>/source_docs/"
```
脚本自动提取 CONFORMED PERIOD OF REPORT 作为日期并保存为 `年报_<公司名>_YYYYMMDD.txt`。

**港股：**
```
# 1. 搜索年报
longbridge filing <CODE> --count 50

# 2. 在结果中找文件名含"年报"的条目（取最新一份），记下 ID

# 3. 获取下载链接
longbridge filing detail <ID> --list-files

# 4. 下载 PDF
curl -L -o "stock-analysis/<名称>/source_docs/年报_<YYYYMMDD>.pdf" "<PDF直链>"
```

**A股：**
```
# 首选：cninfo_download.py 自动处理
python3 scripts/cninfo_download.py <CODE> --name "<公司名>" -o "stock-analysis/<名称>/source_docs/"

# 备用：深交所直链（上述命令失败时）
longbridge filing <CODE> --count 50
# → 搜"年报" → filing detail <ID> --list-files → curl -L 下载
```

### Step 3：确认结果

- 成功下载 → 标记 ✅，文件名 `年报_<公司名>_YYYYMMDD.txt`（美股）或 `年报_<公司名>_YYYYMMDD.pdf`（港股/A股）
- 无法获取 → **停止全部分析**，告知用户"年报不可用，无法继续"

---

## 二、季报 / 中报

### Step 1：确定季报表格类型

| 市场 | 表格类型 | 说明 |
|------|---------|------|
| **美股·中概股** | 6-K | 外国私人发行人定期披露，拿到后按内容区分为半年报或业绩公告 |
| **美股·非中概** | 10-Q | 美国本土公司季度报告 |
| **港股** | 中期报告 PDF | 港股无季报要求，获取半年度"中期报告" |
| **A股** | 季报/半年度报告 | — |

### Step 2：下载季报/中报

**美股（10-Q）：**
```
# 取最近 4 份季报
python3 scripts/sec_filing.py <TICKER> --name "<公司名>" 10-Q --count 4 -o "stock-analysis/<名称>/source_docs/"
```

**美股·中概股（6-K）：**
```
# 取最近 4 份 6-K（包含半年报和业绩公告）
python3 scripts/sec_filing.py <TICKER> --name "<公司名>" 6-K --count 4 -o "stock-analysis/<名称>/source_docs/"
```

**港股：**
```
# 1. 搜索中期报告
longbridge filing <CODE> --count 50

# 2. 在结果中找文件名含"中期报告"的条目，记下 ID

# 3. 获取下载链接
longbridge filing detail <ID> --list-files

# 4. 下载 PDF
curl -L -o "stock-analysis/<名称>/source_docs/季报_<公司名>_<YYYYMMDD>.pdf" "<PDF直链>"
```

**A股：**
```
# 季报（Q1/Q3）
python3 scripts/cninfo_download.py <CODE> --name "<公司名>" --type 季报 -o "stock-analysis/<名称>/source_docs/"

# 中报（H1）
python3 scripts/cninfo_download.py <CODE> --name "<公司名>" --type 半年度报告 -o "stock-analysis/<名称>/source_docs/"
```

### Step 3：确认结果

- 成功下载 → 标记 ✅
- 无法获取 → **停止全部分析**，告知用户"季报不可用，无法继续"

---

## 三、财报电话会议记录

### Step 1：判断是否可获取

| 市场 | 处理方式 |
|------|---------|
| **美股** | 主流途径获取 |
| **美股·双重上市港股** | 使用 US 代码，按美股途径 |
| **纯港股**（仅在港上市） | 无标准英文电话会记录，标记 🚫 注明"纯港股无标准电话会记录" |
| **A股** | `cninfo_download.py` 获取 |

### Step 2：下载电话会记录

**美股（含双重上市的中概股）：**

```
# 1. WebSearch 搜索 Seeking Alpha 文章链接
"<TICKER> <公司名> Q<最新季度> <财年> earnings call transcript seeking alpha"

# 2. 从搜索结果中找到 seekingalpha.com 的 transcript 链接，提取 URL

# 3. WebFetch 获取全文（用步骤 2 拿到的 URL）
# URL 格式参考：https://seekingalpha.com/article/{ARTICLE_ID}-{公司名}-{TICKER}-q{季度}-{财年}-earnings-call-transcript

# 4. 若 Seeking Alpha 需登录或页面不可读，改用备用方案：
"<TICKER> Q<最新季度> <财年> earnings transcript fool.com"
# → 提取 Motley Fool 文章 URL → WebFetch 获取全文
```

**A股：**
```
python3 scripts/cninfo_download.py <STOCK_CODE> --name "<公司名>" --type 电话会 --count 5 -o "stock-analysis/<名称>/source_docs/"
```

### Step 3：保存

将 WebFetch 获取的全文保存为 Markdown 格式：
```
stock-analysis/<名称>/source_docs/电话会纪要_<公司名>_YYYYMMDD.md
```
日期为电话会举办日期（从文章发布时间倒推，通常在财报发布后 1-3 天）。

---

## 四、招股说明书

### Step 1：判断是否需要下载

通过 `longbridge company <CODE>` 查看 `listed_at` 字段，计算上市年数：
- **≤5年** → 必须下载
- **>5年** → 标记 🚫，注明"上市已超5年"，跳过此项

### Step 2：按市场执行下载（≤5年时）

**美股：**
```
# 中概股（代码含 BABA/JD/BIDU/MNSO/PDD/NTES/TCOM/XIACY 等特征）
python3 scripts/sec_filing.py <TICKER> --name "<公司名>" F-1 -o "stock-analysis/<名称>/source_docs/"

# 非中概美股
python3 scripts/sec_filing.py <TICKER> --name "<公司名>" S-1 -o "stock-analysis/<名称>/source_docs/"
```
> 判断中概股的快捷方式：看 `longbridge company` 返回的 `country` 字段是否为 CN，且市场为 US。

**港股：**
```
# 1. 搜索上市文件
longbridge filing <CODE> --count 50

# 2. 在结果中找文件名含"上市文件"或"招股章程"的条目，记下 ID

# 3. 获取下载链接
longbridge filing detail <ID> --list-files

# 4. 下载 PDF
curl -L -o "stock-analysis/<名称>/source_docs/招股书_<YYYYMMDD>.pdf" "<PDF直链>"
```

**A股：**
```
# 1. 搜索招股说明书
longbridge filing <CODE> --count 50

# 2. 在结果中找文件名含"招股说明书"的条目，记下 ID

# 3. 获取下载链接
longbridge filing detail <ID> --list-files

# 4. 下载 PDF
curl -L -o "stock-analysis/<名称>/source_docs/招股书_<YYYYMMDD>.pdf" "<PDF直链>"
```

---

## 五、同行公司年报

### Step 1：找到竞争对手

通过以下任一途径，确定 2-3 家最直接的竞争对手及其股票代码：

**途径 A — 从年报/招股书中提取（最权威）：**
在已下载的年报或招股书中搜索"竞争"/"competition"/"同业"章节，管理层通常在此列出主要竞争对手名称。

**途径 B — Longbridge 行业对比：**
```
longbridge industry-valuation <CODE>
```
此命令返回同行业公司列表及估值对比，从中选取业务最接近的 2-3 家。

**途径 C — WebSearch 辅助：**
搜索 `"<公司名> 竞争对手"` 或 `"<company> competitors peer comparison"`，从搜索结果中提取同行名称，再查代码。

### Step 2：获取同行代码

对每个选定的同行公司，按 Phase 1 的代码解析方法获取其股票代码（WebSearch `"<同行名> 股票代码"`）。

### Step 3：下载同行年报

对每个同行代码，复用第一章"年度报告"的下载命令，保存到同一 `source_docs/` 目录：
```
# 示例：以名创优品(MNSO.US)的同行泡泡玛特(9992.HK)为例
# 先确认泡泡玛特代码 → 9992.HK（港股）
# 按港股年报路径下载：
longbridge filing 9992.HK --count 50
# → 搜"年报" → filing detail <ID> --list-files → curl 下载
```
**文件名格式：** `年报_<公司名称>_<YYYYMMDD>.pdf`（如 `年报_泡泡玛特_20260415.pdf`），与目标公司年报区分。

### Step 4：失败处理

若某同行年报无法获取，标记为 🚫 并注明原因（如"港股通限制"/"SEC未收录"），改用下一家替代。至少获取 1 家同行年报，实在无法获取则全部标记 🚫。

---

## 六、行业研究报告

### 执行流程（逐步骤完成，不可跳过）

#### Step 1：确定搜索关键词

根据公司主营业务确定行业关键词。不确定时，从年报/招股书的"行业分类"章节或 `longbridge company <CODE>` 的 `industry` 字段获取。关键词示例：
- 消费零售类公司 → "零售"、"消费"、"新零售"
- 新能源/电池类 → "锂电池"、"动力电池"、"储能"
- 互联网/科技类 → "互联网"、"云计算"、"人工智能"
- 汽车类 → "整车"、"新能源汽车"

#### Step 2：搜索并获取研报（两种途径，任选一种成功即可）

**途径 A — 东方财富研报中心（首选）：**
以东方财富平台研报为主，只有当东方财富未检索到研报时才走途径B
```
# 1. 用 Chrome DevTools / Playwright 打开搜索页
https://data.eastmoney.com/report/industry.jshtml

# 2. 在搜索框输入行业关键词，等待结果加载

# 3. 从结果列表中点击一篇研报标题，进入正文页

# 4. 在正文页执行 JS 获取 PDF 链接：
javascript_exec: "zwinfo.attach_url"

# 5. 下载 PDF（注意：attach_url 返回的是相对路径，需拼接前缀）
curl -L -o "stock-analysis/<名称>/source_docs/行业研报_<关键词>.pdf" \
  "https://pdf.dfcfw.com/pdf/H3_{infocode}_1.pdf"
```
> 如果无法通过浏览器自动化操作东方财富页面，改用途径 B。

**途径 B — WebSearch 直搜研报 PDF（备用）：**
```
# 搜索词模板（替换 <行业> 和 <年份>）：
"<行业> 行业研究报告 PDF 2026"
"<行业> 年度策略 研报 site:pdf.dfcfw.com"
"<行业> 深度报告 filetype:pdf 2026"

# 从搜索结果中找到 .pdf 直链，直接 curl 下载：
curl -L -o "stock-analysis/<名称>/source_docs/行业研报_<关键词>.pdf" "<PDF直链>"
```

#### Step 3：至少获取 1 份研报

- 成功下载 ≥1 份 → 标记 ✅
- 两种途径均失败 → 标记 🚫，注明"东方财富页面无法访问且 WebSearch 未找到可下载 PDF"

---

## 七、宏观与政策数据

### 执行流程：分成"行业政策"和"宏观经济"两条线，同时进行

#### A 线 — 行业政策（2 条搜索，各打开前 3 个结果 WebFetch 阅读）

**确定搜索关键词：** 用公司所属行业名称 + 政策关键词。行业名从 `longbridge company` 的 `industry` 字段获取。

```
# 搜索 1：国务院/中央层面政策
"<行业名> 政策 国务院 site:gov.cn 2026"
"<行业名> 十四五 规划 2026"

# 搜索 2：部委/监管层面政策
"<行业名> 监管 发改委 2026"
"<行业名> 产业政策 工信部 2026"
```

**操作步骤：**
1. 执行搜索 1，打开前 3 个非重复结果的页面（WebFetch）
2. 执行搜索 2，打开前 3 个非重复结果的页面（WebFetch）
3. 将每条政策的核心内容以 2-3 句话摘要保存到 `source_docs/宏观政策_<行业>.md`

**A股额外步骤：** 如果分析的是 A 股，增加一条搜索 `"<行业名> 政策 site:csrc.gov.cn"`（证监会行业监管）。

#### B 线 — 宏观经济数据（3 个数据源，各获取 1 条关键数据）

根据公司业务的地域分布，选择对应数据源：

**中国宏观（公司业务主要在中国）：**
```
# 1. 国家统计局 — GDP/CPI/PMI
搜索："site:stats.gov.cn GDP 2026 一季度" 或 "site:stats.gov.cn CPI 2026年5月"
WebFetch 打开搜索结果第一个链接，记录关键数字

# 2. 中国人民银行 — 利率/货币政策
搜索："site:pbc.gov.cn LPR 2026" 或 "site:pbc.gov.cn 货币政策执行报告 2026"
WebFetch 打开搜索结果第一个链接，记录关键数字
```

**美国/全球宏观（公司业务涉及美国或全球）：**
```
# 1. FRED 数据库
搜索："site:fred.stlouisfed.org federal funds rate 2026"
或直接 WebFetch: https://fred.stlouisfed.org/series/FEDFUNDS
记录当前利率水平

# 2. 美国 CPI/GDP
搜索："US CPI June 2026 site:bls.gov" 或 "US GDP Q1 2026 site:bea.gov"
```

**保存格式：** 所有宏观数据摘要保存到 `source_docs/宏观政策_<行业>.md`，内容结构：
```markdown
# 宏观与政策数据 — <行业名>

## 一、行业政策动态
| 政策名称 | 发布机构 | 发布日期 | 核心内容摘要 |
|---------|---------|---------|------------|
| ... | ... | ... | ... |

## 二、宏观经济指标
| 指标 | 数值 | 时间 | 数据来源 |
|------|------|------|---------|
| GDP增速 | ... | ... | ... |
| CPI | ... | ... | ... |
| 基准利率 | ... | ... | ... |
```

#### 完成标准

- A 线：至少获取 2 条行业政策摘要
- B 线：至少获取 3 项宏观经济指标
- 两项均达到 → 标记 ✅；某条线数据不足 → 标注原因但不阻塞流程
