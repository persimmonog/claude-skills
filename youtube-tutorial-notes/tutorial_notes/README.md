# 笔记输出目录

此目录用于存放生成的学习笔记。

运行 `process_playlist.py` 后，这里会生成：
- `notes/` - Markdown 格式的学习笔记
- `transcripts/` - 音频转录文本
- `progress.json` - 处理进度记录

## 目录结构

```
tutorial_notes/
├── notes/              # 学习笔记（Markdown）
│   ├── 00_思维导图.md
│   ├── 01_课程标题.md
│   └── ...
├── transcripts/        # 转录文本
│   ├── 01_transcript.txt
│   └── ...
└── progress.json       # 进度文件
```

## 重新生成

如需清空并重新生成所有笔记：

```bash
cd ~/.claude/skills/youtube-tutorial-notes
rm -rf tutorial_notes/notes/* tutorial_notes/transcripts/*
python3 process_playlist.py
```
