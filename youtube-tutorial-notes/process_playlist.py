#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理整个YouTube播放列表：下载→转录→保存转录文件→生成manifest
AI步骤（review、笔记生成、思维导图）由 Claude agent 处理
"""
import sys
import json
import os
import time
from pathlib import Path

# 添加scripts目录到路径
script_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(script_dir))

from download_video import download_video
from transcribe_audio import transcribe_video


def get_config():
    """读取配置文件"""
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def parse_playlist(file_path):
    """解析播放列表文件"""
    videos = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or '|||' not in line:
                continue
            parts = line.split('|||')
            if len(parts) == 2:
                title, url = parts
                videos.append({'title': title.strip(), 'url': url.strip()})
    return videos


def save_progress(index, total, title, output_dir):
    """保存进度"""
    progress_file = output_dir / "progress.json"
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump({
            'current': index,
            'total': total,
            'last_video': title,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }, f, ensure_ascii=False, indent=2)


def process_video(index, video, config, output_dir, video_dir):
    """处理单个视频：下载→转录→保存"""
    title = video['title']
    url = video['url']
    print(f"\n{'='*60}")
    print(f"处理 [{index}/{video.get('total', '?')}]: {title}")
    print(f"{'='*60}")

    video_file = None
    transcription_config = config.get('transcription', {})
    model_size = transcription_config.get('model_size', 'base')
    device = transcription_config.get('device', 'cpu')
    language = transcription_config.get('language', 'auto')

    try:
        # 1. 检查或下载音频
        print(f"\n[1/3] 检查音频...")

        existing_files = []
        for pattern in [f"{title}.*"]:
            existing_files.extend(video_dir.glob(pattern))

        # 模糊匹配
        if not existing_files:
            for f in video_dir.glob('*'):
                if title in f.name:
                    existing_files.append(f)

        if existing_files:
            video_path = existing_files[0]
            file_size = video_path.stat().st_size
            print(f"✅ 找到现有文件: {video_path.name} ({file_size / 1024 / 1024:.2f} MB)")
        else:
            print(f"⬇️  开始下载...")
            video_file = download_video(url, str(video_dir))

            if not video_file:
                print(f"❌ 下载失败: {title}")
                return False

            video_path = Path(video_file)
            if not video_path.exists():
                print(f"❌ 文件不存在: {video_file}")
                return False

            file_size = video_path.stat().st_size
            print(f"✅ 下载完成: {video_path.name} ({file_size / 1024 / 1024:.2f} MB)")

        # 2. 转录音频
        print(f"\n[2/3] 转录音频...")
        transcript = transcribe_video(
            str(video_path),
            model_size=model_size,
            device=device,
            language=language
        )

        if not transcript:
            print(f"❌ 转录失败: {title}")
            return False

        print(f"✅ 转录完成，长度: {len(transcript)} 字符")

        # 3. 保存转录文件
        print(f"\n[3/3] 保存转录文件...")
        transcript_dir = output_dir / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)

        transcript_file = transcript_dir / f"{index:02d}_{title}.txt"
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(transcript)

        print(f"💾 转录已保存: {transcript_file.name}")

        # 清理音频文件
        video_path.unlink()
        print(f"🗑️  已清理音频文件")

        # 返回元数据
        return {
            'index': index,
            'title': title,
            'url': url,
            'transcript_file': str(transcript_file.name)
        }

    except Exception as e:
        print(f"\n❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()

        # 清理可能残留的文件
        if video_file and Path(video_file).exists():
            try:
                Path(video_file).unlink()
                print(f"🗑️  已清理失败的音频文件")
            except:
                pass

        return False


def main():
    """主函数"""
    cwd = Path.cwd()
    output_dir = cwd / "tutorial_notes"
    video_dir = cwd / "temp_videos"

    # 读取配置
    config = get_config()

    # 解析播放列表
    playlist_file = Path(__file__).parent / "playlist_new.txt"
    videos = parse_playlist(playlist_file)

    if not videos:
        print("❌ 播放列表为空或格式错误")
        sys.exit(1)

    print(f"📹 播放列表共 {len(videos)} 个视频")
    print(f"📁 工作目录: {cwd}")
    print(f"📁 输出目录: {output_dir}\n")

    # 创建目录
    output_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)

    # 处理每个视频
    results = []
    failed_videos = []

    for i, video in enumerate(videos, start=1):
        video['total'] = len(videos)  # 传入总数用于显示
        result = process_video(i, video, config, output_dir, video_dir)
        if result:
            results.append(result)
            save_progress(i, len(videos), video['title'], output_dir)
        else:
            failed_videos.append(f"{i}. {video['title']}")

    # 生成 manifest
    manifest = {
        'videos': results,
        'total': len(videos),
        'success': len(results),
        'failed': failed_videos,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }

    manifest_file = output_dir / "transcripts" / "manifest.json"
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 打印总结
    print(f"\n{'='*60}")
    print(f"✅ 处理完成!")
    print(f"{'='*60}")
    print(f"成功: {len(results)}/{len(videos)}")

    if failed_videos:
        print(f"\n❌ 失败的视频 ({len(failed_videos)}):")
        for video in failed_videos:
            print(f"   - {video}")

    print(f"\n📄 Manifest: {manifest_file}")
    print(f"\n下一步: 读取 manifest.json，由 Claude agent 生成笔记和思维导图")


if __name__ == "__main__":
    main()
