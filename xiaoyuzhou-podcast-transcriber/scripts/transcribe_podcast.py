#!/usr/bin/env python3
"""
小宇宙播客转录脚本
支持从小宇宙播客链接提取音频并使用本地 faster-whisper 模型转录为文字稿

优化版本：
- 自动检测并安装依赖
- 直接从小宇宙页面提取音频链接下载
- 只输出完整文本（不带时间戳）
"""

import argparse
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path


def check_and_install_dependencies():
    """检查并自动安装必要的依赖"""
    dependencies = [
        ('faster_whisper', 'faster-whisper', 'Whisper 语音识别模型'),
        ('opencc', 'opencc-python-reimplemented', '中文简繁转换库'),
        ('certifi', 'certifi', 'SSL 证书验证'),
    ]

    missing = []
    for module_name, pip_name, description in dependencies:
        try:
            __import__(module_name)
        except ImportError:
            missing.append((pip_name, description))

    if missing:
        print("=" * 50)
        print("检测到缺少以下依赖，正在自动安装...")
        for pip_name, desc in missing:
            print(f"  - {pip_name}: {desc}")
        print("=" * 50)

        for pip_name, _ in missing:
            try:
                print(f"\n正在安装 {pip_name}...")
                result = subprocess.run(
                    ['pip3', 'install', pip_name, '--quiet'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode != 0:
                    print(f"安装 {pip_name} 失败: {result.stderr}")
                    print(f"请手动运行: pip3 install {pip_name}")
                    return False
                print(f"✓ {pip_name} 安装成功")
            except subprocess.TimeoutExpired:
                print(f"安装 {pip_name} 超时，请手动运行: pip3 install {pip_name}")
                return False
            except Exception as e:
                print(f"安装 {pip_name} 时出错: {e}")
                return False

        print("\n所有依赖安装完成！")

    return True


def extract_episode_id(url: str) -> str:
    """从小宇宙URL中提取episode ID"""
    pattern = r'xiaoyuzhoufm\.com/episode/([a-zA-Z0-9]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    raise ValueError(f"无法从URL中提取episode ID: {url}")


def get_episode_info(episode_id: str) -> dict:
    """获取播客节目信息，包括音频URL"""
    url = f"https://www.xiaoyuzhoufm.com/episode/{episode_id}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    req = urllib.request.Request(url, headers=headers)

    try:
        ssl_context = get_ssl_context()
        with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
            html = response.read().decode('utf-8')

            # 提取标题
            title_match = re.search(r'<title>(.*?)</title>', html)
            title = title_match.group(1) if title_match else episode_id
            # 清理小宇宙平台后缀："XXX - 播客名 | 小宇宙 - 听播客，上小宇宙"
            title = re.sub(r'\s*[-|]\s*小宇宙.*$', '', title)

            # 直接提取音频URL（小宇宙音频链接格式）
            audio_patterns = [
                r'(https://media\.xyzcdn\.net/[^\s"\'<>]+\.(?:m4a|mp3))',
                r'(https://[^\s"\'<>]*\.xyzcdn\.net/[^\s"\'<>]+\.(?:m4a|mp3))',
                r'"(https://[^\s"\'<>]+\.(?:m4a|mp3))"',
            ]

            audio_url = None
            for pattern in audio_patterns:
                audio_match = re.search(pattern, html)
                if audio_match:
                    audio_url = audio_match.group(1)
                    audio_url = audio_url.replace('\\u002F', '/').replace('\\/', '/')
                    break

            return {
                'id': episode_id,
                'title': title,
                'url': url,
                'audio_url': audio_url
            }
    except Exception as e:
        print(f"获取节目信息失败: {e}")
        return {
            'id': episode_id,
            'title': episode_id,
            'url': url,
            'audio_url': None
        }


def download_audio_direct(audio_url: str, output_path: str, title: str = "音频") -> bool:
    """直接下载音频文件，显示下载进度"""
    print(f"正在下载: {title}")
    print(f"音频链接: {audio_url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://www.xiaoyuzhoufm.com/',
    }

    req = urllib.request.Request(audio_url, headers=headers)

    try:
        ssl_context = get_ssl_context()
        with urllib.request.urlopen(req, context=ssl_context, timeout=60) as response:
            total_size = response.getheader('Content-Length')
            if total_size:
                total_size = int(total_size)
                size_mb = total_size / (1024 * 1024)
                print(f"文件大小: {size_mb:.1f} MB")

            downloaded = 0
            chunk_size = 8192
            last_percent = -1

            with open(output_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size:
                        percent = int(downloaded * 100 / total_size)
                        if percent != last_percent and percent % 10 == 0:
                            print(f"下载进度: {percent}%")
                            last_percent = percent

        print(f"✓ 下载完成: {output_path}")
        return True

    except Exception as e:
        print(f"下载失败: {e}")
        return False


def smart_paragraph_split(segments: list, min_gap: float = 0.5) -> str:
    """
    根据语音停顿和标点分割段落，自动添加中文标点

    Args:
        segments: 带时间戳的片段列表
        min_gap: 触发段落分割的最小停顿时间（秒）

    Returns:
        分段后的文本
    """
    if not segments:
        return ""

    # 过滤掉无意义的短停顿和填充词，避免过度分段
    filler_words = {'对吧', '是吧', '嗯', '啊', '哦', '那么', '然后', '其实', '当然', '就是说',
                    '就是', '对吧', '好的', '好吧', '嗯嗯', '嗯好', '这个', '那个', '所以说'}

    paragraphs = []
    current_para = []
    para_char_count = 0

    for i, seg in enumerate(segments):
        text = re.sub(r'\s+', '', seg['text'])  # 去除所有空白字符
        if text in filler_words:
            continue

        current_para.append(text)
        para_char_count += len(text)

        if i < len(segments) - 1:
            gap = segments[i + 1]['start'] - seg['end']
            next_seg = segments[i + 1]['text'].strip()

            # 检查是否需要分段
            should_split = False
            is_last_in_para = False

            # 大停顿（>1秒）直接分段
            if gap >= 1.0 and current_para:
                should_split = True
                is_last_in_para = True
            # 句号/问号/叹号结尾 + 停顿≥0.3秒分段
            elif ends_with_punct(text, ('。', '？', '！', '?', '!', '.', '」', '”')) and gap >= 0.3:
                should_split = True
                is_last_in_para = True
            # 逗号/分号结尾 + 停顿≥0.5秒分段
            elif ends_with_punct(text, ('，', ',', '；', ';')) and gap >= 0.5:
                should_split = True
                is_last_in_para = True
            # 段落超过35个字符强制分段
            elif para_char_count >= 35 and current_para:
                should_split = True
                is_last_in_para = True

            if should_split and current_para:
                # 给段落最后一个片段加标点（如果没有）
                last_text = current_para[-1]
                if last_text and not last_text[-1] in '。？！.?!"\'，,' :
                    last_char = last_text[-1]
                    if '\u4e00' <= last_char <= '\u9fff' or '\uac00' <= last_char <= '\ud7af':
                        current_para[-1] = last_text + '，'

                paragraphs.append(''.join(current_para))
                current_para = []
                para_char_count = 0

    # 添加最后一段（加句号）
    if current_para:
        last_text = current_para[-1]
        if last_text and not last_text[-1] in '。？！.?!"\'，,':
            last_char = last_text[-1]
            if '\u4e00' <= last_char <= '\u9fff' or '\uac00' <= last_char <= '\ud7af':
                current_para[-1] = last_text + '。'
        paragraphs.append(''.join(current_para))

    return '\n\n'.join(paragraphs)


def ends_with_punct(text: str, punctuations: tuple) -> bool:
    """检查文本是否以指定标点结尾（去除尾随空格后）"""
    stripped = text.strip()
    return stripped.endswith(punctuations)


def clean_repeated_text(segments: list) -> list:
    """
    清理转录结果中的重复片段
    例如："围的围的围的围的" 会被合并为 "围的"
    """
    if not segments:
        return segments

    cleaned = []
    for seg in segments:
        text = seg['text']
        # 检测并折叠连续重复模式（如 "围的围的围的围的"）
        # 尝试匹配 2-5 字符的子串重复 3 次以上
        for word_len in range(5, 1, -1):
            pattern = r'(.{' + str(word_len) + r'})\1{3,}'
            text = re.sub(pattern, r'\1', text)
        cleaned.append({
            'start': seg['start'],
            'end': seg['end'],
            'text': text
        })
    return cleaned


def get_ssl_context():
    """获取 SSL 上下文，优先使用 certifi 的 CA bundle"""
    import ssl
    import certifi
    context = ssl.create_default_context(cafile=certifi.where())
    return context


def convert_to_simplified_chinese(text: str) -> str:
    """
    将繁体中文转换为简体中文
    如果 opencc 不可用，返回原文
    """
    try:
        import opencc
        converter = opencc.OpenCC('t2s')  # 繁体转简体
        return converter.convert(text)
    except ImportError:
        # 如果 opencc 不可用，返回原文
        return text


def transcribe_audio(audio_path: str, model_size: str = "base", language: str = "zh",
                     output_path: str = None, device: str = None, title: str = None) -> str:
    """
    使用 faster-whisper 转录音频
    中文播客自动转换为简体中文输出

    Args:
        audio_path: 音频文件路径
        model_size: Whisper 模型大小
        language: 语言代码
        output_path: 输出文件路径
        device: 计算设备
        title: 节目标题（用于输出文件标题行）
    """
    from faster_whisper import WhisperModel

    # 自动检测设备
    if device is None or device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    print(f"\n加载模型: {model_size}, 设备: {device}")
    print("(首次使用某模型时会自动下载，请耐心等待...)")

    # 加载模型
    model = WhisperModel(model_size, device=device, compute_type="float16" if device == "cuda" else "int8")

    print("开始转录...")

    # 转录音频
    segments, info = model.transcribe(audio_path, language=language, beam_size=5,
                                      condition_on_previous_text=True)

    print(f"检测到语言: {info.language}, 概率: {info.language_probability:.2f}")
    print(f"音频时长: {info.duration:.1f} 秒 ({info.duration/60:.1f} 分钟)")

    # 收集所有文本
    full_text = []
    segments_with_timestamps = []
    segment_count = 0
    for segment in segments:
        segment_count += 1
        text = segment.text.strip()
        if text:
            full_text.append(text)
            segments_with_timestamps.append({
                'start': segment.start,
                'end': segment.end,
                'text': text
            })

        if segment_count % 50 == 0:
            print(f"已处理 {segment_count} 个片段...")

    print(f"✓ 转录完成，共 {segment_count} 个片段")

    # 清理重复片段
    segments_with_timestamps = clean_repeated_text(segments_with_timestamps)

    # 如果检测到中文语言，转换为简体中文
    detected_lang = info.language
    if detected_lang in ('zh', 'chinese', 'yue'):  # zh=普通话, yue=粤语
        print("检测到中文，转换为简体中文...")
        # 同时转换带时间戳的文本
        for seg in segments_with_timestamps:
            seg['text'] = convert_to_simplified_chinese(seg['text'])
        print("✓ 已转换为简体中文")

    # 合并文本
    final_text = ' '.join(seg['text'] for seg in segments_with_timestamps)
    if detected_lang in ('zh', 'chinese', 'yue'):
        final_text = convert_to_simplified_chinese(final_text)

    # 段落分割处理（根据停顿时间自动分段）
    paragraph_text = smart_paragraph_split(segments_with_timestamps)

    # 构建输出
    display_title = title if title else (output_path.stem if output_path else '播客文字稿')
    transcript_lines = []
    transcript_lines.append(f"# {display_title}\n\n")
    transcript_lines.append(f"**转录信息**: 模型 {model_size} | 时长 {info.duration/60:.1f} 分钟\n\n")
    transcript_lines.append(f"---\n\n")

    # 段落分割处理（根据停顿时间自动分段）
    transcript_lines.append(paragraph_text)

    transcript = "".join(transcript_lines)

    # 保存到文件
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(transcript)
        print(f"\n✓ 文字稿已保存到: {output_path}")

    return transcript


def main():
    parser = argparse.ArgumentParser(
        description="小宇宙播客转录工具 - 将播客音频转换为文字稿",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s "https://www.xiaoyuzhoufm.com/episode/xxx"
  %(prog)s "https://www.xiaoyuzhoufm.com/episode/xxx" -m small -o 输出.md
  %(prog)s "https://www.xiaoyuzhoufm.com/episode/xxx" --audio-path 本地音频.m4a
        """
    )
    parser.add_argument("url", help="小宇宙播客链接")
    parser.add_argument("-o", "--output", help="输出文件路径", default=None)
    parser.add_argument("-m", "--model", help="Whisper模型大小 (默认: base)",
                        default="base", choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"])
    parser.add_argument("-l", "--language", help="语言代码 (默认: zh)", default="zh")
    parser.add_argument("-d", "--device", help="计算设备 (cpu/cuda/auto, 默认: auto)", default="auto")
    parser.add_argument("--keep-audio", help="保留下载的音频文件", action="store_true")
    parser.add_argument("--audio-only", help="仅下载音频，不转录", action="store_true")
    parser.add_argument("--audio-path", help="使用本地音频文件，跳过下载")
    parser.add_argument("--no-install", help="跳过自动安装依赖", action="store_true")

    args = parser.parse_args()

    # 设置环境变量解决 OpenMP 库冲突
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

    # 检查并安装依赖
    if not args.no_install:
        if not check_and_install_dependencies():
            sys.exit(1)

    # 验证URL并提取episode ID
    episode_id = None
    if not args.audio_path:
        try:
            episode_id = extract_episode_id(args.url)
            print(f"✓ Episode ID: {episode_id}")
        except ValueError as e:
            print(f"错误: {e}")
            sys.exit(1)

    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        if args.audio_path:
            output_path = Path(args.audio_path).with_suffix('.md')
        else:
            output_path = Path(f"podcast_{episode_id}.md")

    # 确定音频路径
    episode_title = None
    if args.audio_path:
        audio_path = Path(args.audio_path)
        if not audio_path.exists():
            print(f"错误: 音频文件不存在: {audio_path}")
            sys.exit(1)
        print(f"✓ 使用本地音频: {audio_path}")
    else:
        # 获取节目信息并提取音频URL
        print(f"\n正在获取节目信息...")
        info = get_episode_info(episode_id)
        print(f"节目标题: {info['title']}")
        episode_title = info['title']

        if not info['audio_url']:
            print("错误: 无法从页面提取音频链接")
            print("提示: 可能需要登录或页面结构已变化，请手动下载音频后使用 --audio-path 参数")
            sys.exit(1)

        # 创建输出目录
        audio_dir = Path.home() / "Downloads" / "podcast_transcript"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / f"{episode_id}.m4a"

        # 下载音频
        print()
        if not download_audio_direct(info['audio_url'], str(audio_path), info['title']):
            sys.exit(1)

        # 更新输出路径使用节目标题
        if not args.output:
            safe_title = re.sub(r'[<>:"/\\|?*]', '', info['title'])[:50]
            output_path = audio_dir / f"{safe_title}_文字稿.md"

    # 如果只需要音频，到此结束
    if args.audio_only:
        print(f"\n✓ 音频已保存到: {audio_path}")
        sys.exit(0)

    # 转录音频
    print()
    try:
        transcript = transcribe_audio(
            audio_path=str(audio_path),
            model_size=args.model,
            language=args.language,
            output_path=output_path,
            device=args.device,
            title=episode_title
        )

        print(f"\n{'='*50}")
        print(f"转录完成！")
        print(f"文字稿: {output_path}")
        if not args.audio_path and args.keep_audio:
            print(f"音频文件: {audio_path}")
        print(f"{'='*50}")

    except Exception as e:
        print(f"转录失败: {e}")
        sys.exit(1)

    finally:
        # 清理临时文件
        if not args.audio_path and not args.keep_audio:
            try:
                if audio_path.exists():
                    audio_path.unlink()
                    print(f"\n(临时音频文件已清理，使用 --keep-audio 保留)")
            except:
                pass


if __name__ == "__main__":
    main()