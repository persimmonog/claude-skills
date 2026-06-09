# 各市场申报文件下载指南

> 仅包含各市场原始文件的**下载命令**。信息提取要求见 `references/critical_data_extraction.md`。
> 执行流程由 SKILL.md Phase 2 第 2a 层驱动，本文件按需查阅对应章节。

---

## 通用保存规范

- **保存位置：** `source_docs/`，文件名格式 `类型_YYYYMMDD.txt`（如 `年报_20260409.txt`）
- **保存内容：** 一手原始文档全文
- **日期来源：** 美股从 SEC 头部 `CONFORMED PERIOD OF REPORT` 提取；港股从 `longbridge filing` 的 `publish_at` 列提取；A股从巨潮 API 返回的 `announcementDate` 字段提取（cninfo_download.py 自动处理）

---

## 一、年度报告

### 获取方式

| 市场 | 命令 |
|------|------|
| **美股** | `python3 scripts/sec_filing.py <TICKER> 10-K -o "stock-analysis/<名称>/source_docs/"` |
| **美股·中概股** | `python3 scripts/sec_filing.py <TICKER> 20-F -o "stock-analysis/<名称>/source_docs/"` |
| **港股** | `longbridge filing <CODE> --count 50` 搜"年报" → `filing detail <ID> --list-files` 获PDF直链 → `curl -L -o "stock-analysis/<名称>/source_docs/年报_<YYYYMMDD>.pdf" "<PDF直链>"` 下载PDF |
| **A股** | `python3 scripts/cninfo_download.py <CODE> -o "stock-analysis/<名称>/source_docs/"`（首选）；备用：`longbridge filing` 深交所直链 |

---

## 二、季报 / 中报

### 获取方式

| 市场 | 命令 |
|------|------|
| **美股** | `python3 scripts/sec_filing.py <TICKER> 10-Q --count 4 -o "stock-analysis/<名称>/source_docs/"` |
| **美股·中概股** | `python3 scripts/sec_filing.py <TICKER> 6-K --count 4 -o "stock-analysis/<名称>/source_docs/"`（6-K 是外国私人发行人的定期披露表格；中概股无季报要求，此处获取的通常是半年报和业绩公告，注意按文件内容区分） |
| **港股** | `longbridge filing <CODE> --count 50` 搜"中期报告" → `filing detail <ID> --list-files` 获PDF直链 → `curl -L -o "stock-analysis/<名称>/source_docs/季报_<YYYYMMDD>.pdf" "<PDF直链>"` 下载PDF |
| **A股** | `python3 scripts/cninfo_download.py <CODE> --type 季报 -o "stock-analysis/<名称>/source_docs/"`（中报用 `--type 半年度报告`） |

---

## 三、财报电话会议记录

### 获取方式

| 市场 | 命令 |
|------|------|
| **美股** | WebSearch 搜索 `"<TICKER> <公司名> Q<季度> <财年> earnings call transcript seeking alpha"` → 提取 Seeking Alpha 文章 URL → WebFetch 获取全文 |
| **美股·双重上市港股** | 纯港股不获取；双重上市公司（BABA/JD/BIDU等）按美股途径，使用 US 代码 |
| **A股** | `python3 scripts/cninfo_download.py <STOCK_CODE> --type 电话会 --count 5 -o "stock-analysis/<名称>/source_docs/"` |

> **美股 URL 模板（以 NVDA 为例）：** `https://seekingalpha.com/article/4907259-nvidia-corporation-nvda-q1-2027-earnings-call-transcript`
> 模板：`https://seekingalpha.com/article/{ARTICLE_ID}-{公司名}-{TICKER}-q{季度}-{财年}-earnings-call-transcript`
> 注意：`{ARTICLE_ID}` 为数字 ID，需通过 WebSearch 获取，无法直接拼出。
>
> **备用方案（Seeking Alpha 需 JS/登录时）：** WebSearch 搜索 `"<TICKER> Q<季度> <财年> earnings transcript fool.com"` → Motley Fool 版获取。
>
> **保存规范：** 获取全文后，保存至 `stock-analysis/<名称>/source_docs/电话会纪要_YYYYMMDD.md`，使用 Markdown 格式。文件名示例：`电话会纪要_20260520.md`。

---

## 四、招股说明书

### 获取方式

| 市场 | 命令 |
|------|------|
| **美股** | `python3 scripts/sec_filing.py <TICKER> S-1 -o "stock-analysis/<名称>/source_docs/"`（中概用 F-1） |
| **港股** | `longbridge filing <CODE> --count 50` 搜"上市文件" → `filing detail <ID> --list-files` 获PDF直链 → `curl -L -o "stock-analysis/<名称>/source_docs/招股书_<YYYYMMDD>.pdf" "<PDF直链>"` 下载PDF |
| **A股** | `longbridge filing <CODE> --count 50` 搜"招股说明书" → `filing detail <ID> --list-files` 获PDF直链 → `curl -L -o "stock-analysis/<名称>/source_docs/招股书_<YYYYMMDD>.pdf" "<PDF直链>"` 下载PDF（巨潮 API 暂不支持招股书搜索） |

---

## 五、同行公司年报

选取 2-3 家最直接的竞争对手，对其年报按第一章的获取命令执行，保存到同一 `source_docs/` 目录下（文件名加同行代码前缀区分）。

---

## 六、行业研究报告

### 获取途径

1. **东方财富研报中心（行业研报）** → `data.eastmoney.com/report/industry.jshtml`
   - 搜索目标行业（如"整车"、"电池"、"消费电子"）
   - 点开报告正文页，页面 JS 变量 `zwinfo.attach_url` 即为 PDF 地址
   - 下载格式：`https://pdf.dfcfw.com/pdf/H3_{infocode}_1.pdf?{timestamp}.pdf`
2. **WebSearch 辅助发现：** `"<行业> 研报 site:data.eastmoney.com/report 2026"` — 仅用于找报告链接，内容走 PDF

---

## 七、宏观与政策数据

### 获取途径

**行业政策：**
1. **WebSearch：** `"<行业名> 政策 国务院 site:gov.cn"` 或 `"<行业> 监管 发改委"`
2. 北大法宝 (lawinfochina.com) 搜索行业关键词

**宏观经济：**
1. 国家统计局 (stats.gov.cn) —— 中国宏观数据
2. FRED (fred.stlouisfed.org) —— 美国及全球数据
3. 中国人民银行 (pbc.gov.cn) —— 货币政策、利率
