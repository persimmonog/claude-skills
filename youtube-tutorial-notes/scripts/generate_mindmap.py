#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成思维导图
自动读取所有笔记文件并生成思维导图
"""

import sys
import json
from pathlib import Path

# 添加脚本路径
sys.path.insert(0, str(Path(__file__).parent))

from gemini_streaming import GeminiStreamingClient


def generate_mindmap(config_path: str = None, notes_dir: str = None) -> str:
    """
    生成思维导图

    Args:
        config_path: 配置文件路径
        notes_dir: 笔记目录路径

    Returns:
        生成的思维导图内容（Markdown格式）
    """
    # 默认路径
    if config_path is None:
        config_path = str(Path(__file__).parent.parent / "config.json")
    if notes_dir is None:
        notes_dir = str(Path.cwd() / "tutorial_notes" / "notes")

    # 读取配置
    with open(config_path, 'r') as f:
        config = json.load(f)

    gemini = GeminiStreamingClient(config['gemini']['api_key'], config['gemini']['model'])

    # 自动读取所有笔记文件（排除00_开头的思维导图文件）
    notes_dir = Path(notes_dir)
    note_files = sorted([f for f in notes_dir.glob("*.md") if not f.name.startswith("00_")])

    if len(note_files) == 0:
        print("⚠️ 未找到笔记文件")
        return ""

    print(f"找到 {len(note_files)} 个笔记文件")

    # 读取所有笔记
    all_notes = []
    for notes_file in note_files:
        with open(notes_file, 'r', encoding='utf-8') as f:
            all_notes.append(f.read())

    # 合并所有笔记
    combined_notes = "\n\n".join(all_notes)

    # 生成思维导图
    prompt = f"""你是专业的学习助手。请根据以下{len(note_files)}节课程的学习笔记，生成一个精简的思维导图。

**课程笔记内容**：

{combined_notes}

**要求**：
1. 使用 Mermaid 格式的思维导图（mindmap）
2. 只包含核心知识点，用于引导复习
3. 去除概述、总结等非核心内容
4. 结构精简，层级清晰（最多3-4层）
5. 只包含笔记中实际提到的内容，不要添加外部知识

请直接输出 Mermaid 格式的思维导图代码，不需要其他说明文字。

输出格式示例：
```mermaid
mindmap
  root((课程主题))
    知识领域1
      核心概念1
        要点1
        要点2
      核心概念2
    知识领域2
      概念3
      概念4
```

只输出思维导图代码，不要有其他解释。
"""

    mindmap = gemini.generate_content(prompt, max_tokens=8192)

    if not mindmap:
        print("✗ 思维导图生成失败")
        return ""

    # 清理输出（移除可能的markdown代码块标记）
    mindmap = mindmap.strip()
    if mindmap.startswith('```'):
        # 找到第一个换行符
        first_newline = mindmap.find('\n')
        last_newline = mindmap.rfind('\n')
        if first_newline != -1 and last_newline != -1:
            mindmap = mindmap[first_newline+1:last_newline].strip()

    return f"# 课程学习笔记 - 思维导图\n\n{mindmap}"


if __name__ == "__main__":
    print("="*80)
    print("生成思维导图")
    print("="*80)

    # 解析命令行参数
    notes_dir = sys.argv[1] if len(sys.argv) > 1 else None

    # 生成思维导图
    mindmap = generate_mindmap(notes_dir=notes_dir)

    if not mindmap:
        sys.exit(1)

    # 保存到文件
    if notes_dir:
        output_file = Path(notes_dir) / "00_思维导图.md"
    else:
        output_file = Path.cwd() / "tutorial_notes" / "notes" / "00_思维导图.md"

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(mindmap)

    print(f"\n✓ 思维导图生成完成")
    print(f"  字数: {len(mindmap)}")
    print(f"  保存至: {output_file}")

    print("\n" + "="*80)
    print("✓ 全部完成！")
    print("="*80)
