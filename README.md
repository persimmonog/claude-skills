# Persimmon Skills

一组可复用技能（Skills），覆盖信息采集、内容创作、数据分析、媒体处理和本地工具等场景。

## 技能列表

| 技能 | 用途 |
| --- | --- |
| [ai-news-collector](ai-news-collector/) | 采集头部 AI 公司官方博客的近期文章，并整理为中文摘要 |
| [ai-social-collector](ai-social-collector/) | 采集社交媒体和自媒体中的 AI 讨论、观点与评论 |
| [article-to-storyboard](article-to-storyboard/) | 将文章或故事转换为 AI 视频分镜脚本 |
| [city-cultural-events](city-cultural-events/) | 查询和推荐城市文化活动、展览与演出 |
| [contemporary-allegory-print](contemporary-allegory-print/) | 将主题、意象或照片创作为当代寓言版画海报 |
| [idea-to-storyboard](idea-to-storyboard/) | 将一句场景创意扩展为约 10 秒的 AI 视频分镜 |
| [stock-analysis](stock-analysis/) | 基于公开资料完成股票基本面分析 |
| [x-video-downloader](x-video-downloader/) | 下载 X（Twitter）视频，支持断点续传 |
| [xiaoyuzhou-podcast-transcriber](xiaoyuzhou-podcast-transcriber/) | 下载并使用 faster-whisper 转录小宇宙播客 |
| [youtube-tutorial-notes](youtube-tutorial-notes/) | 将 YouTube 播放列表转换为结构化学习笔记 |

每个技能目录中的 `SKILL.md` 是该技能的主要说明文件，包含触发场景、工作流程和使用约定。部分技能还提供脚本、参考资料、配置文件或评估用例。

## 使用方式

将需要的技能目录复制到 Claude Code 的技能目录中，例如：

```bash
cp -R ai-news-collector ~/.claude/skills/
```

也可以直接将本仓库中的技能目录放入你的技能加载路径。安装后，在 Claude Code 中用自然语言描述对应任务即可触发技能；具体命令和参数请以各目录中的 `SKILL.md` 为准。

## 运行环境

- Python 3
- 部分技能需要额外的 Python 依赖，详见对应目录的 README、`requirements.txt` 或 `SKILL.md`
- 视频、播客和部分数据采集技能可能依赖网络访问以及本地媒体处理工具
- 需要 API Key、Cookies 或其他凭据的技能，请根据对应目录中的示例配置进行设置

## 目录结构

```text
.
├── ai-news-collector/
├── ai-social-collector/
├── article-to-storyboard/
├── city-cultural-events/
├── contemporary-allegory-print/
├── idea-to-storyboard/
├── stock-analysis/
├── x-video-downloader/
├── xiaoyuzhou-podcast-transcriber/
└── youtube-tutorial-notes/
```

## 开发与贡献

新增或修改技能时，建议：

1. 为技能目录编写清晰的 `SKILL.md`，说明名称、触发场景、输入输出和工作流程。
2. 将可重复执行的逻辑放入 `scripts/`，将框架、指南等资料放入 `references/`。
3. 涉及密钥、Cookies 或本地路径时，提供脱敏后的示例配置。
4. 在提交前运行相关脚本或按技能说明完成手动验证。

欢迎提交 Issue 或 Pull Request，分享新的技能、修复和改进建议。

## 开源协议

本项目采用 [MIT License](LICENSE) 开源。各技能所依赖的第三方服务、数据源、模型和素材，仍受其各自的使用条款和许可证约束。
