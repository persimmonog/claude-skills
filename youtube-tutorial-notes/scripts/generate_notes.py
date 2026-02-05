#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从转录文本生成学习笔记
原子化功能：只负责从单个转录生成笔记
"""

import sys
import json
from pathlib import Path

# 添加脚本路径
sys.path.insert(0, '/Users/luyonghui/.claude/skills/youtube-tutorial-notes/scripts')

from gemini_streaming import GeminiStreamingClient


def generate_notes(transcript: str, video_title: str, config_path: str = "./config.json") -> str:
    """
    从转录文本生成学习笔记

    Args:
        transcript: 转录文本
        video_title: 视频标题
        config_path: 配置文件路径

    Returns:
        生成的笔记内容（Markdown格式）
    """
    # 读取配置
    with open(config_path, 'r') as f:
        config = json.load(f)

    # 初始化Gemini客户端
    gemini = GeminiStreamingClient(config['gemini']['api_key'], config['gemini']['model'])

    # 生成笔记的提示词
    prompt = f"""你是专业的学习笔记助手。请根据以下课程转录文本生成精简的学习笔记。

**重要原则**：
1. 只记录必须要的核心内容，去除冗余
2. 不添加课程概述、总结等非必要内容
3. 只基于转录文本中的内容，不添加外部知识
4. 不要编造课程中未提及的公式、代码或例子

**视频信息**：
- 标题：{video_title}
- 转录文本：{transcript}

请生成以下结构的笔记（用 Markdown 格式）：

---
# {video_title}

## 核心知识点

### 知识点1：标题
**核心内容**：（精简描述概念和要点，基于转录文本）

**关键细节**：（如果有重要的细节、公式或代码，记录在这里；如果没有，省略）

---

请确保：
1. 只保留核心知识点，去除概述、总结等
2. 内容精简，直击要害
3. 所有内容都来自转录文本
4. 不添加外部知识或例子
"""

    print(f"生成笔记: {video_title}")
    notes = gemini.generate_content(prompt, max_tokens=8192)

    if not notes:
        print("✗ 笔记生成失败")
        return ""

    print(f"✓ 笔记生成完成 (字数: {len(notes)})")
    return notes


def save_notes(notes: str, output_file: str) -> bool:
    """
    保存笔记到文件

    Args:
        notes: 笔记内容
        output_file: 输出文件路径

    Returns:
        是否保存成功
    """
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(notes)

        print(f"✓ 笔记已保存: {output_file}")
        return True

    except Exception as e:
        print(f"✗ 保存失败: {e}")
        return False


if __name__ == "__main__":
    # 测试生成笔记
    if len(sys.argv) < 3:
        print("用法: python generate_notes.py <transcript_file> <video_title> [output_file]")
        sys.exit(1)

    transcript_file = sys.argv[1]
    video_title = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None

    # 读取转录文本
    with open(transcript_file, 'r', encoding='utf-8') as f:
        transcript = f.read()

    # 生成笔记
    notes = generate_notes(transcript, video_title)

    if notes:
        # 保存笔记
        if output_file:
            save_notes(notes, output_file)
        else:
            print("\n" + "="*80)
            print(notes)
            print("="*80)
    else:
        sys.exit(1)
