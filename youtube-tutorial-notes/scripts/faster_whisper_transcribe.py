#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 faster-whisper 转录音频

本地运行，无需 API，速度快
"""

from faster_whisper import WhisperModel
import pathlib


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
            compute_type="int8"
        )
        print(f"✓ 模型加载完成")

    def transcribe(self, audio_path: str, language: str = "auto") -> str:
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
                vad_filter=True,
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

                if segment_count % 10 == 0:
                    print(f"    已处理 {segment_count} 个片段...")

            transcript = "".join(full_text)

            print(f"  ✓ 转录完成，共 {segment_count} 个片段")
            return transcript

        except Exception as e:
            print(f"  ✗ 转录失败: {e}")
            import traceback
            traceback.print_exc()
            return None
