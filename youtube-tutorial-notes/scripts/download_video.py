#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最简单的YouTube视频下载脚本
"""

import subprocess
from pathlib import Path


def download_video(video_url: str, output_dir: str = "./temp_videos") -> str:
    """
    下载YouTube视频

    Args:
        video_url: YouTube视频URL
        output_dir: 输出目录

    Returns:
        下载的文件路径
    """
    # 创建输出目录
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 获取 cookies.txt 文件路径
    script_dir = Path(__file__).parent.parent
    cookies_file = script_dir / "cookies.txt"

    # 检查 cookies 文件是否存在
    if not cookies_file.exists():
        print(f"⚠️ 警告: cookies.txt 文件不存在")
        print(f"   期望路径: {cookies_file}")

    # 下载命令（只下载音频，转录够用且更快）
    cmd = [
        "yt-dlp",
        "--js-runtimes", "node:/usr/local/bin/node",  # 添加JS运行时
        "--remote-components", "ejs:github",  # 启用远程JS挑战解决
        "--cookies", str(cookies_file),  # 使用 cookies.txt
        "--format", "bestaudio/best",  # 只下载音频
        "--extract-audio",  # 提取音频
        "--audio-format", "m4a",  # 音频格式
        "--audio-quality", "0",  # 最佳质量
        "--no-playlist",  # 不下载播放列表
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        video_url
    ]

    print(f"正在下载: {video_url}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        # 从输出中提取文件名
        for line in result.stdout.split('\n'):
            if '[download] Destination:' in line:
                file_path = line.split('[download] Destination: ')[1]
                print(f"✅ 下载完成: {file_path}")
                return file_path

        # 如果没找到，查找最新文件
        files = list(Path(output_dir).glob('*.mp4')) + list(Path(output_dir).glob('*.m4a')) + list(Path(output_dir).glob('*.mp3')) + list(Path(output_dir).glob('*.webm'))
        if files:
            latest = max(files, key=lambda f: f.stat().st_mtime)
            print(f"✅ 下载完成: {latest}")
            return str(latest)

    print(f"❌ 下载失败")
    print(result.stderr)
    return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python download_video.py <YouTube_URL>")
        sys.exit(1)

    download_video(sys.argv[1])
