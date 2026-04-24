# 小宇宙播客转录工具

使用本地 faster-whisper 模型将小宇宙播客链接转换为 Markdown 格式文字稿。

## 功能特点

- **一键转录**：从小宇宙链接下载音频 → 本地语音识别 → 生成 Markdown 文字稿
- **智能分段**：根据语音停顿和标点自动分段，段落间空行分隔
- **自动添加标点**：段落末尾自动补充逗号/句号
- **去重清理**：自动折叠连续重复片段（如思考停顿导致的"围的围的围的"）
- **标题提取**：自动获取节目标题，输出文件名和内容标题一致
- **中文优化**：简体中文输出、繁体自动转换
- **SSL 安全**：使用 certifi CA bundle 验证证书
- **断点续传**：支持 `--audio-path` 使用本地音频重新转录
- **多模型支持**：tiny/base/small/medium/large/large-v2/large-v3
- **CPU/GPU 自动检测**

## 前置要求

```bash
pip3 install faster-whisper opencc-python-reimplemented certifi
```

## 使用方法

### 基本用法

```bash
python3 scripts/transcribe_podcast.py "https://www.xiaoyuzhoufm.com/episode/xxxxxxxx"
```

输出保存到 `~/Downloads/podcast_transcript/<节目标题>_文字稿.md`

### 指定输出文件

```bash
python3 scripts/transcribe_podcast.py "https://www.xiaoyuzhoufm.com/episode/xxxxxxxx" -o "输出.md"
```

### 指定模型

```bash
# 更快但精度较低
python3 scripts/transcribe_podcast.py "URL" -m base

# 更高精度
python3 scripts/transcribe_podcast.py "URL" -m medium
```

### 保留音频

```bash
python3 scripts/transcribe_podcast.py "URL" --keep-audio
```

### 仅下载音频

```bash
python3 scripts/transcribe_podcast.py "URL" --audio-only
```

### 使用本地音频

```bash
python3 scripts/transcribe_podcast.py "URL" --audio-path "/path/to/audio.m4a"
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `url` | 小宇宙播客链接 | 必需 |
| `-o, --output` | 输出文件路径 | 自动生成 |
| `-m, --model` | Whisper 模型大小 | base |
| `-l, --language` | 语言代码 | zh |
| `-d, --device` | 计算设备 | auto |
| `--keep-audio` | 保留音频文件 | 否 |
| `--audio-only` | 仅下载音频 | 否 |
| `--audio-path` | 使用本地音频 | - |
| `--no-install` | 跳过自动安装依赖 | 否 |

## 输出格式

```markdown
# 节目标题

**转录信息**: 模型 base | 时长 15.4 分钟

---

第一段内容，

第二段内容。

第三段内容，
```

- 中文文本紧凑无空格
- 段落末尾自动添加逗号/句号
- 段落间空行分隔

## 模型选择建议

| 模型 | 速度 | 准确度 | 适用场景 |
|------|------|--------|----------|
| tiny | 最快 | 较低 | 快速预览 |
| base | 快 | 中等 | 日常使用（推荐） |
| small/medium | 中等 | 较高 | 需要较高准确度 |
| large/large-v3 | 最慢 | 最高 | 最高精度要求 |

## 注意事项

1. **首次运行**：首次使用某模型时会自动下载（base 约 140MB，large-v3 约 3GB）
2. **转录时间**：CPU 模式下约 1 小时音频需要 10-30 分钟转录
3. **音频保存**：默认保存在 `~/Downloads/podcast_transcript/`
4. **macOS 问题**：脚本自动处理 OpenMP 库冲突问题

## 故障排除

### 无法提取音频链接

- 确认链接格式正确
- 尝试手动下载音频后使用 `--audio-path` 参数

### 转录速度慢

- 尝试更小的模型（tiny/base）
- 如有 NVIDIA GPU，确保 CUDA 和 PyTorch 已正确安装

### 内存不足

- 使用更小的模型
