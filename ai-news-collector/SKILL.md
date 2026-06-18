---
name: ai-news-collector
description: 采集头部 AI 公司官方博客最新文章并按中文格式输出。触发场景：用户询问 AI 行业最新动态、头部 AI 公司最新发布、今日 AI 新闻、AI 公司博客更新；用户提到 OpenAI/Anthropic/xAI/智谱 等公司名并要求获取最新信息；用户需要 AI 领域前沿研究或产品动态汇总。数据来源为各公司官方博客，只采集近两日（昨日至今日）发布的内容。
---

# AI 头部信息采集 Skill

## 概述

脚本采集 + Claude 分析。脚本负责抓取和过滤，Claude 负责阅读正文并生成中文摘要。

**关键优化**：脚本抓取文章列表时会一并获取正文内容，Claude 直接从输出中读取，无需额外 HTTP 请求。

## 工作流程

```
1. 运行脚本 (JSON模式)   → 输出包含 {title, link, date, content} 的完整数据
2. 读取 content   → 从脚本输出中直接获取文章正文，不重复请求
3. 生成摘要       → 提炼核心观点、引语、数据
```

## 执行

```bash
python3 <skill-dir>/scripts/collect_news.py 2>/dev/null
```

脚本默认 JSON 输出。每篇文章的 `content` 字段包含清洗后的文章正文（最多 2500 字符），Claude 直接据此写摘要。

## 摘要要求

不要只抄第一段。好的摘要应该有：

- **引语引用** — 直接引述原文关键表述
- **核心主张** — "这篇文章在说什么，为什么值得看"
- **具体信息** — 含数字、对比、具体案例
- **中文意译** — 2-4 句话，自然流畅

## 输出格式样例

```
# AI 头部公司动态（5月25日 - 5月26日）

---

## Anthropic

**1. Anthropic 联合创始人 Chris Olah 就教皇 AI 通谕发表评论**
Olah 在梵蒂冈坦承"每个前沿 AI 实验室——包括 Anthropic——都运行在可能与做正确事情相冲突的激励机制中"，并指出 AI 大规模取代劳动后对失业者的支持是"历史级别的道德挑战"。
https://anthropic.com/news/chris-olah-pope-leo-encyclical

---

## OpenAI

暂无更新
```

## 数据来源

| 公司 | URL | 方式 |
|------|-----|------|
| **OpenAI** | `https://openai.com/blog/rss.xml` | RSS |
| **Anthropic** | `https://anthropic.com/news` | HTML |
| **Anthropic 研究** | `https://anthropic.com/research` | HTML |
| **Nous Research** | `https://nousresearch.com/blog/` | HTML |
| **Hugging Face** | `https://huggingface.co/blog/feed.xml` | RSS |
| **Google DeepMind** | `https://deepmind.google/blog/rss.xml` | RSS |
| **Google AI** | `https://blog.research.google/rss.xml` | RSS |
| **xAI** | `https://x.ai/news` | HTML |

## 注意事项

- **时间窗口**：昨日 00:00 至今日 23:59
- **摘要来源**：使用脚本输出的 `content` 字段，不要额外 curl
- **content 为空**：说明该文章页无法抓取（客户端渲染/反爬），如实标注即可
