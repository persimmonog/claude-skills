---
name: ai-social-collector
description: 采集社交媒体和自媒体上关于 AI 的讨论与观察。触发场景：用户想知道社区/自媒体怎么看待最近的 AI 动态、大家都在讨论什么 AI 话题、各平台对某个 AI 事件的热议。数据来源包括 V2EX、Reddit、TechCrunch、少数派，只采集近两日（昨日至今日）的内容。
---

# AI 社媒信息采集 Skill

## 概述

脚本采集 + Claude 分析。采集各社交媒体和自媒体平台近两日的 AI 相关热门讨论，附带用户评论，Claude 负责阅读内容并生成中文摘要。

## 工作流程

```
1. 运行脚本 (JSON模式)  → 输出 {title, link, score, content, comments} 完整数据
2. Claude 读取内容      → 从 content/comments 字段直接获取，不重复请求
3. 生成摘要            → 提炼讨论焦点、社区情绪、争议点
```

## 执行

```bash
python3 <skill-dir>/scripts/collect_social.py 2>/dev/null
```

输出 JSON，每项包含 title、link、热度指标、正文内容、评论详情。

## 数据来源

| 平台 | URL | 方式 | 说明 |
|------|-----|------|------|
| **V2EX /go/ai** | `https://www.v2ex.com/go/ai` | HTML 解析 | 中文社区 AI 讨论，有回复数 |
| **Reddit r/artificial** | `https://www.reddit.com/r/artificial/.json` | JSON API | 含分数、评论数、精确时间戳 |
| **Reddit r/singularity** | `https://www.reddit.com/r/singularity/.json` | JSON API | 关注 AGI/超人类智能，讨论偏未来向 |
| **Hacker News** | `https://news.ycombinator.com/rss` | RSS（关键词过滤） | 英文技术社区，AI 话题自动筛选，含评论 |
| **TechCrunch AI** | `https://techcrunch.com/category/artificial-intelligence/feed/` | RSS | AI 行业英文媒体 |
| **少数派** | `https://sspai.com/feed` | RSS | 中文自媒体，关注效率工具+AI |

### 尝试过但不可达
- **GitHub Trending** — 内容以代码仓库为主，非讨论
- **36kr** — 客户端渲染，爬虫不可达
- **即刻** — 连接超时
- **知乎** — 需登录

## 摘要要求

- **讨论焦点** — 社区在争论什么、关注什么
- **社区情绪** — 是兴奋、担忧还是嘲讽
- **争议点** — 如果有 opposing views，提炼出来
- **中文意译** — 2-4 句话

## 输出格式（必须严格遵守）

Claude **必须**按照以下固定格式逐字输出，不增不减，不改变顺序，不调整标题层级，不省略任何部分。

### 格式模板

```
# AI 社媒讨论动态（{起止日期}）

---

## {平台名称}

**1. {帖子标题 (👍{分数} 💬{评论数})}**
{2-4 句话中文摘要：讨论焦点、社区情绪、争议点}
https://{原文链接}

**热门评论:**
- 👍{分数} "{评论内容}"
- 👍{分数} "{评论内容}"
- 👍{分数} "{评论内容}"

---

## {下一个平台}

暂无更新

---

## {下一个平台}

暂无更新
```

### 格式规则

1. **标题**：`# AI 社媒讨论动态（M月D日 - M月D日）`，日期范围精确
2. **平台分区**：用 `---` 分隔，平台名使用 `##`
3. **帖子条目**：`**序号. 标题 (👍{热度} 💬{回复数})**`，序号从 1 开始递增
4. **摘要**：帖子标题下一行，2-4 句中文意译
5. **链接**：摘要下一行，原文 URL
6. **热门评论**：仅 Reddit 和 HN 可以加 `**热门评论:**` 区块，其他平台不加
7. **评论内容**：`- 👍{分数} "{评论原文}"`（英文评论保持英文，中文评论保持中文）
8. **热门评论不超过 3 条**：按分数排序，只输出最高的 2-3 条
9. **无更新**：平台没有近两日数据时，输出 "暂无更新"
10. **不包含个人总结或结束语**：输出到此结束，不加 "以上是..." 或 "趋势总结"

### 平台展示顺序

必须严格按照以下顺序：
1. Reddit r/singularity
2. Reddit r/artificial
3. Hacker News
4. TechCrunch AI
5. V2EX /go/ai
6. 少数派

## 注意事项

- **时间窗口**：昨日 00:00 至今日 23:59
- **摘要来源**：使用脚本输出的 `content` 和 `comments_detail` 字段
- **content 为空**：说明页面无法抓取，如实标注
- **Reddit 评论**：脚本会自动获取前 5 条最热评论
