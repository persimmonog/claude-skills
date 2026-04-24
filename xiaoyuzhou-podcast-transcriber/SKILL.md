---
name: 小宇宙播客转录工具
description: 将小宇宙播客链接转换为文字稿，使用本地 faster-whisper 模型进行语音识别。当 Claude 需要转录小宇宙播客节目为文字稿、下载播客音频、或提取播客内容进行分析时使用此工具。中文播客自动输出简体中文，英文播客输出英文。
---

# 小宇宙播客转录工具

使用本地 faster-whisper 模型将小宇宙播客链接转换为 Markdown 格式文字稿。

## 功能特点

- 支持从小宇宙播客链接提取音频
- 使用本地 faster-whisper 模型进行语音识别
- 生成 Markdown 格式文字稿
- **中文播客自动转换为简体中文输出**
- 英文播客保持英文输出
- 支持多种模型大小（tiny/base/small/medium/large）
- 支持 CPU/CUDA 自动检测
- 支持断点续传（手动指定音频文件）
- **智能段落分割**（根据语音停顿自动分段）
- 自动清理重复片段（如思考停顿导致的重复内容）

## 前置要求

### 安装依赖

```bash
# 安装 faster-whisper（必需）
pip3 install faster-whisper

# 安装 opencc（中文简繁转换，必需）
pip3 install opencc-python-reimplemented

# 安装 certifi（SSL 证书验证，必需）
pip3 install certifi

# 可选：安装 PyTorch（如果使用 GPU 加速）
pip3 install torch
```

### 模型下载

faster-whisper 首次使用时会自动下载模型到本地缓存目录。

## 使用方法

### 基本用法

转录单个小宇宙播客链接（默认使用 base 模型）：

```bash
python3 scripts/transcribe_podcast.py "https://www.xiaoyuzhoufm.com/episode/xxxxxxxx"
```

### 指定输出文件

```bash
python3 scripts/transcribe_podcast.py "https://www.xiaoyuzhoufm.com/episode/xxxxxxxx" \
    -o "我的播客稿.md"
```

### 使用较小的模型（更快但精度较低）

```bash
python3 scripts/transcribe_podcast.py "https://www.xiaoyuzhoufm.com/episode/xxxxxxxx" \
    -m base
```

### 仅下载音频

```bash
python3 scripts/transcribe_podcast.py "https://www.xiaoyuzhoufm.com/episode/xxxxxxxx" \
    --audio-only --keep-audio
```

### 使用本地音频文件（断点续传）

如果下载中断或需要重新转录已下载的音频：

```bash
python3 scripts/transcribe_podcast.py "https://www.xiaoyuzhoufm.com/episode/xxxxxxxx" \
    --audio-path "/path/to/audio.m4a"
```

## Claude 使用指南

当用户请求转录小宇宙播客时：

1. **检查依赖**：确认已安装 faster-whisper、opencc 和 certifi
2. **选择模型**：默认使用 base 模型（速度快），若用户要求高质量转录可用 medium/small
3. **运行脚本**：使用 `transcribe_podcast.py` 进行转录
5. **整理文本**：读取生成的 Markdown 文件，按以下规则整理后展示给用户

### 文本整理规则

Whisper 转录的中文文本带有基本标点（逗号、句号），但专有名词识别率较低。展示给用户前，**必须**对完整文本部分做一次整理：

**必须修正的错误**：
- 明显的错别字（如"通脏"→"通胀"、"脱口袖"→"脱口秀"）
- 确定能判断的专有名词（如上下文能推断出"开疯娥使"是"Kevin Warsh"）

**不需要修正的**：
- 不确定的专有名词（如无法确认原文，保留即可）
- 口语化的表达（如语气词、口语重复）

**不需要修正的**：
- 口语化的表达（如语气词、口语重复）
- 英文专有名词的发音式拼写（如果无法确定原文，保留即可）

**整理方式**：
- 直接编辑 Markdown 文件中的"完整文本"部分
- 修正后向用户说明整理过的内容
- 如果文本量很大（超过 30 分钟音频），可以只整理明显影响理解的错误

### 示例流程

用户："帮我把这个小宇宙播客转成文字稿：https://www.xiaoyuzhoufm.com/episode/abc123"

Claude 应该：

1. 运行：`python3 scripts/transcribe_podcast.py "URL"`
2. 等待转录完成
3. 读取 `.md` 文件，整理完整文本部分的错别字和标点
4. 展示整理后的文字稿给用户，并简要说明修正了哪些内容

## 输出格式

输出为简洁的 Markdown 格式：

```markdown
# 节目标题

**转录信息**: 模型 base | 时长 45.2 分钟

---

第一段内容，

第二段内容。

第三段内容，
```

脚本自动处理：
- 中文文本无多余空格，段落间自然分段
- 段落末尾自动添加逗号/句号
- 自动清理重复片段（如"围的围的围的"）

## 注意事项

1. **音频下载**：小宇宙的音频通常可以直接下载。如果自动下载失败，可能需要登录，建议用户手动下载音频后使用 `--audio-path` 参数
2. **模型选择**：
   - base（默认）：速度快，适合日常使用
   - small/medium：平衡速度和准确度，适合长音频和专有名词较多的内容
   - large/large-v2/large-v3：最高准确度，但模型体积大（约 3GB），首次下载较慢
3. **GPU 加速**：如果有 NVIDIA GPU 和 CUDA，转录速度会大幅提升
4. **首次运行**：第一次使用某模型时会自动下载，可能需要一些时间

## 故障排除

### 下载失败

如果无法自动下载音频：

1. 使用浏览器访问播客页面
2. 使用浏览器开发者工具或扩展手动下载音频
3. 使用 `--audio-path` 参数指定下载的音频文件

### 转录速度慢

- 尝试更小的模型（tiny/base）
- 使用 GPU（自动检测）
- 确保 PyTorch 已正确安装

### 内存不足

- 使用更小的模型
- 对于长音频，可以使用分段处理（需要额外脚本）

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `url` | 小宇宙播客链接 | 必需 |
| `-o, --output` | 输出文件路径 | 自动生成 |
| `-m, --model` | Whisper 模型大小 | base |
| `-l, --language` | 语言代码 | zh |
| `-d, --device` | 计算设备 | auto |
| `--keep-audio` | 保留下载的音频文件 | 否 |
| `--audio-only` | 仅下载音频，不转录 | 否 |
| `--audio-path` | 使用本地音频文件 | - |
| `--no-install` | 跳过自动安装依赖 | 否 |