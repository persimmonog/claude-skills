#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini Streaming API 调用脚本

使用 REST API + streaming 模式，避免 SDK 超时问题
"""

import requests
import json
import time
from typing import Generator


class GeminiStreamingClient:
    """Gemini 流式 API 客户端"""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """
        初始化客户端

        参数:
            api_key: Gemini API 密钥
            model: 模型名称
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def generate_content_stream(self, prompt: str, max_tokens: int = 8192) -> Generator[str, None, None]:
        """
        流式生成内容

        参数:
            prompt: 提示词
            max_tokens: 最大输出 tokens

        返回:
            生成器，每次返回一段文本
        """
        url = f"{self.base_url}/models/{self.model}:streamGenerateContent?key={self.api_key}"

        headers = {
            'Content-Type': 'application/json',
        }

        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": max_tokens
            }
        }

        try:
            # 使用流式响应
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=30,  # 连接超时 30 秒
                stream=True  # 启用流式响应
            )
            response.raise_for_status()

            # streaming API 返回的是 JSON 数组（每行一个对象）
            full_response = ""

            # 读取所有行并组合成完整的 JSON 数组
            for line in response.iter_lines():
                if line:
                    full_response += line.decode('utf-8')

            # 解析 JSON 数组
            try:
                chunks = json.loads(full_response)

                # 遍历每个 chunk
                for chunk_data in chunks:
                    # 提取文本
                    if 'candidates' in chunk_data and len(chunk_data['candidates']) > 0:
                        candidate = chunk_data['candidates'][0]
                        if 'content' in candidate and 'parts' in candidate['content']:
                            for part in candidate['content']['parts']:
                                if 'text' in part:
                                    yield part['text']

            except json.JSONDecodeError as e:
                print(f"⚠️ JSON 解析错误: {e}")
                print(f"原始响应: {full_response[:500]}...")

        except requests.exceptions.Timeout:
            print(f"\n⚠️ 连接超时，但可能已有部分内容")
        except Exception as e:
            print(f"\n✗ 错误: {e}")
            raise

    def generate_content(self, prompt: str, max_tokens: int = 8192) -> str:
        """
        非流式生成内容（自动收集所有流式响应）

        参数:
            prompt: 提示词
            max_tokens: 最大输出 tokens

        返回:
            完整文本
        """
        full_text = ""
        for chunk in self.generate_content_stream(prompt, max_tokens):
            full_text += chunk
        return full_text


def test_streaming():
    """测试流式 API"""
    # 读取配置
    with open('/Users/luyonghui/.claude/skills/youtube-tutorial-notes/config.json', 'r') as f:
        config = json.load(f)
        api_key = config['gemini']['api_key']

    client = GeminiStreamingClient(api_key)

    print("="*80)
    print("测试 Gemini Streaming API")
    print("="*80)

    prompt = """请详细分析XXX主题的核心概念，包括：
1. 概念1的定义和实现
2. 概念2的作用
3. 概念3的应用
4. 概念4的类型

请用中文回答，每个概念用一段完整段落描述。"""

    print("\n开始流式接收响应:\n")
    print("-"*80)

    try:
        full_text = ""
        char_count = 0

        for chunk in client.generate_content_stream(prompt):
            print(chunk, end='', flush=True)
            full_text += chunk
            char_count += len(chunk)

        print("\n" + "-"*80)
        print(f"\n✓ 接收完成！")
        print(f"总字符数: {char_count}")

        # 保存结果
        with open('/Users/luyonghui/.claude/skills/youtube-tutorial-notes/streaming_test_output.txt', 'w', encoding='utf-8') as f:
            f.write(full_text)

        print(f"✓ 结果已保存到 streaming_test_output.txt")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_streaming()
