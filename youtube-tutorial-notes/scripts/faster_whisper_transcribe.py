#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 faster-whisper 转录音频

本地运行，无需 API，速度快
"""

from faster_whisper import WhisperModel
import pathlib
import sys


class FasterWhisperTranscriber:
    """faster-whisper 转录器"""

    def __init__(self, model_size: str = "base", device: str = "cpu"):
        """
        初始化转录器

        参数:
            model_size: 模型大小 (tiny/base/small/medium/large)
            device: 运行设备 (cpu/cuda)
        """
        print(f"加载 faster-whisper 模型 ({model_size})...")
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type="int8"  # 使用 int8 量化，更快且省内存
        )
        print(f"✓ 模型加载完成")

    def transcribe(self, audio_path: str, language: str = "zh") -> str:
        """
        转录音频文件

        参数:
            audio_path: 音频文件路径
            language: 语言代码 (zh=中文, en=英文, auto=自动检测)

        返回:
            转录文本
        """
        print(f"  转录中...")

        try:
            segments, info = self.model.transcribe(
                audio_path,
                language=language if language != "auto" else None,
                beam_size=5,
                vad_filter=True,  # 启用 VAD 过滤静音
                vad_parameters={
                    "min_silence_duration_ms": 500,
                    "speech_pad_ms": 300
                }
            )

            # 收集所有段落
            full_text = []
            segment_count = 0

            for segment in segments:
                full_text.append(segment.text)
                segment_count += 1

                # 每10段打印一次进度
                if segment_count % 10 == 0:
                    print(f"    已处理 {segment_count} 个片段...")

            # 合并文本
            transcript = "".join(full_text)

            print(f"  ✓ 转录完成，共 {segment_count} 个片段")
            return transcript

        except Exception as e:
            print(f"  ✗ 转录失败: {e}")
            import traceback
            traceback.print_exc()
            return None


def test_transcription():
    """测试转录功能"""

    print("="*80)
    print("测试 faster-whisper")
    print("="*80)

    # 创建转录器
    transcriber = FasterWhisperTranscriber(model_size="base", device="cpu")

    # 测试音频文件
    test_audio = "/Users/luyonghui/.claude/skills/youtube-tutorial-notes/test_download/test_video.mp4"

    if not pathlib.Path(test_audio).exists():
        print(f"✗ 测试音频不存在: {test_audio}")
        return

    print(f"\n测试音频: {test_audio}")
    file_size = pathlib.Path(test_audio).stat().st_size / 1024 / 1024
    print(f"文件大小: {file_size:.2f} MB")

    # 转录
    print("\n开始转录...")
    transcript = transcriber.transcribe(test_audio, language="zh")

    if transcript:
        print("\n" + "="*80)
        print("转录成功！")
        print("="*80)
        print(f"\n转录文本（前500字符）:\n")
        print(transcript[:500])
        print(f"\n总字数: {len(transcript)}")

        # 保存结果
        output_file = '/Users/luyonghui/.claude/skills/youtube-tutorial-notes/test_transcript.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(transcript)

        print(f"\n✓ 完整转录已保存到: {output_file}")
    else:
        print("\n✗ 转录失败")


if __name__ == '__main__':
    test_transcription()
