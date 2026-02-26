---
name: x-video-downloader
description: X (Twitter) 视频下载工具，支持断点续传。当 Claude 需要从 X/Twitter 下载视频时使用此技能： (1) 将 Twitter 视频保存到本地，(2) 处理中断的下载（支持断点续传），(3) 从推文中获取高质量 MP4 视频。脚本支持断点续传、自动重试，并下载可用的最高质量 MP4 格式。
---

# X 视频下载器

## 快速开始

下载 Twitter/X 视频：

```bash
python3 scripts/download_x_video.py <推文链接>
```

示例：
```bash
python3 scripts/download_x_video.py https://x.com/user/status/1234567890
```

## 功能特性

- **高质量下载**：自动下载最佳 MP4 质量
- **断点续传**：下载中断后自动恢复（断点续传）
- **自动重试**：最多 10 次重试，确保下载成功
- **视频信息**：下载前显示标题、作者、时长等信息

## 使用方法

使用任何 X/Twitter 推文链接运行脚本：

```bash
python3 scripts/download_x_video.py https://x.com/username/status/1234567890
python3 scripts/download_x_video.py https://twitter.com/username/status/1234567890
```

视频将保存到当前目录，文件名格式为：`%(title)s_%(id)s.%(ext)s`

## 环境要求

- Python 3
- yt-dlp：`pip install yt-dlp`
