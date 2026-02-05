#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从视频文件转录音频
原子化功能：只负责转录单个视频
"""

import sys
from pathlib import Path

# 添加脚本路径
sys.path.insert(0, '/Users/luyonghui/.claude/skills/youtube-tutorial-notes/scripts')

from faster_whisper_transcribe import FasterWhisperTranscriber


def transcribe_video(video_path: str, model_size: str = "base", device: str = "cpu") -> str:
    """
    转录视频音频为文本

    Args:
        video_path: 视频文件路径
        model_size: 模型大小 (tiny/base/small/medium/large)
        device: 设备类型 (cpu/cuda)

    Returns:
        转录文本
    """
    # 检查文件是否存在
    if not Path(video_path).exists():
        print(f"✗ 视频文件不存在: {video_path}")
        return ""

    # 初始化转录器
    print(f"加载 faster-whisper 模型 ({model_size})...")
    transcriber = FasterWhisperTranscriber(model_size=model_size, device=device)
    print("✓ 模型加载完成")

    # 转录
    print(f"转录音频: {video_path}")
    transcript = transcriber.transcribe(video_path, language="zh")

    if not transcript:
        print("✗ 转录失败")
        return ""

    print(f"✓ 转录完成 (字数: {len(transcript)})")
    return transcript


def save_transcript(transcript: str, output_file: str) -> bool:
    """
    保存转录文本到文件

    Args:
        transcript: 转录文本
        output_file: 输出文件路径

    Returns:
        是否保存成功
    """
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(transcript)

        print(f"✓ 转录已保存: {output_file}")
        return True

    except Exception as e:
        print(f"✗ 保存失败: {e}")
        return False


if __name__ == "__main__":
    # 测试转录
    if len(sys.argv) < 2:
        print("用法: python transcribe_audio.py <video_file> [output_file]")
        sys.exit(1)

    video_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    # 转录
    transcript = transcribe_video(video_file)

    if transcript:
        # 保存转录
        if output_file:
            save_transcript(transcript, output_file)
        else:
            print("\n" + "="*80)
            print(transcript)
            print("="*80)
    else:
        sys.exit(1)
