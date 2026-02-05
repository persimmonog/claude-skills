#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Review和修正转录文本
原子化功能：修正转录中的错别字、标点等问题
"""

import sys
import json
from pathlib import Path

# 添加脚本路径
sys.path.insert(0, '/Users/luyonghui/.claude/skills/youtube-tutorial-notes/scripts')

from gemini_streaming import GeminiStreamingClient


def review_transcript(transcript: str, config_path: str = "./config.json", max_retries: int = 2) -> str:
    """
    Review和修正转录文本

    Args:
        transcript: 原始转录文本
        config_path: 配置文件路径
        max_retries: 最大重试次数

    Returns:
        修正后的转录文本（如果review失败则返回原始文本）
    """
    # 读取配置
    with open(config_path, 'r') as f:
        config = json.load(f)

    # 初始化Gemini客户端
    gemini = GeminiStreamingClient(config['gemini']['api_key'], config['gemini']['model'])

    # 如果转录太长，跳过review（避免超时）
    if len(transcript) > 10000:
        print("⚠️ 转录文本过长，跳过review步骤")
        return transcript

    # Review提示词（简化版，减少处理时间）
    prompt = f"""你是专业的文本校对员。请快速review以下转录文本，只修正明显的错别字。

**转录文本**（前3000字）：
{transcript[:3000]}

**修正规则**：
1. 只修正明显的错别字
2. 修正标点符号
3. 保持原意，不改变内容

请直接输出修正后的前3000字文本。
"""

    # 重试机制（减少重试次数）
    for attempt in range(max_retries):
        try:
            print(f"Review转录文本... (尝试 {attempt + 1}/{max_retries})")

            # 使用更短的超时时间
            import time
            start_time = time.time()

            reviewed = gemini.generate_content(prompt, max_tokens=4000)

            if reviewed and len(reviewed) > 100:
                print(f"✓ Review完成 (字数: {len(reviewed)})")
                # 如果review成功，返回review后的文本
                return reviewed + transcript[3000:]  # 拼接剩余部分
            else:
                if attempt < max_retries - 1:
                    print("⚠️ Review结果为空，15秒后重试...")
                    time.sleep(15)
                    continue

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️ Review出错: {e}，15秒后重试...")
                import time
                time.sleep(15)
                continue

    # Review失败，返回原始文本
    print("⚠️ Review失败，使用原始转录")
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
    # 测试review
    if len(sys.argv) < 2:
        print("用法: python review_transcript.py <transcript_file> [output_file]")
        sys.exit(1)

    transcript_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    # 读取转录
    with open(transcript_file, 'r', encoding='utf-8') as f:
        transcript = f.read()

    # Review
    reviewed = review_transcript(transcript)

    if reviewed:
        # 保存
        if output_file:
            save_transcript(reviewed, output_file)
        else:
            print("\n" + "="*80)
            print("修正后的文本:")
            print("="*80)
            print(reviewed)
            print("="*80)
    else:
        sys.exit(1)
