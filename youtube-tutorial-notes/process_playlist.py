#!/usr/bin/env python3
"""
处理整个YouTube播放列表：下载→转录→review→生成笔记
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
from review_transcript import review_transcript
from generate_notes import generate_notes


def get_config_path():
    """获取配置文件路径"""
    return str(Path(__file__).parent / "config.json")


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


def process_video(index, video, config_path, output_dir, video_dir):
    """处理单个视频"""
    title = video['title']
    url = video['url']
    print(f"\n{'='*60}")
    print(f"处理 [{index}/28]: {title}")
    print(f"{'='*60}")

    video_file = None

    try:
        # 1. 检查或下载音频
        print(f"\n[1/4] 检查音频...")

        # 先检查是否已有音频文件（支持多种格式）
        existing_files = []
        for ext in ['*.webm', '*.m4a', '*.mp3', '*.mp4']:
            existing_files.extend(video_dir.glob(f"{title}.*"))
            existing_files.extend(video_dir.glob(f"{title}.{ext}"))

        # 如果找不到精确匹配，尝试模糊匹配
        if not existing_files:
            for f in video_dir.glob('*'):
                if title in f.name:
                    existing_files.append(f)

        if existing_files:
            # 使用现有文件
            video_path = existing_files[0]
            file_size = video_path.stat().st_size
            print(f"✅ 找到现有文件: {video_path.name} ({file_size / 1024 / 1024:.2f} MB)")
        else:
            # 下载新文件
            print(f"⬇️  开始下载...")
            video_file = download_video(url, str(video_dir))

            if not video_file:
                print(f"❌ 下载失败: {title}")
                return False

            # 检查文件是否存在
            video_path = Path(video_file)
            if not video_path.exists():
                print(f"❌ 文件不存在: {video_file}")
                return False

            file_size = video_path.stat().st_size
            print(f"✅ 下载完成: {video_path.name} ({file_size / 1024 / 1024:.2f} MB)")

        # 2. 转录音频
        print(f"\n[2/4] 转录音频...")
        transcript = transcribe_video(str(video_path))

        if not transcript:
            print(f"❌ 转录失败: {title}")
            return False

        print(f"✅ 转录完成，长度: {len(transcript)} 字符")

        # 3. Review转录文本
        print(f"\n[3/4] Review转录文本...")
        reviewed_transcript = review_transcript(transcript, config_path)

        if not reviewed_transcript:
            print(f"⚠️ Review失败，使用原始转录")
            reviewed_transcript = transcript
        else:
            print(f"✅ Review完成")

        # 4. 生成笔记
        print(f"\n[4/4] 生成笔记...")
        notes = generate_notes(reviewed_transcript, title, config_path)

        if not notes:
            print(f"❌ 笔记生成失败: {title}")
            return False

        print(f"✅ 笔记生成完成")

        # 5. 保存文件
        transcript_file = output_dir / "transcripts" / f"{index:02d}_transcript.txt"
        notes_file = output_dir / "notes" / f"{index:02d}_{title}.md"

        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(reviewed_transcript)

        with open(notes_file, 'w', encoding='utf-8') as f:
            f.write(notes)

        print(f"\n💾 保存完成:")
        print(f"   - 转录: {transcript_file.name}")
        print(f"   - 笔记: {notes_file.name}")

        # 6. 清理音频文件
        video_path.unlink()
        print(f"🗑️  已清理音频文件")

        return True

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
    # 使用当前工作目录
    cwd = Path.cwd()
    output_dir = cwd / "tutorial_notes"
    video_dir = cwd / "temp_videos"

    # 获取配置文件路径
    config_path = get_config_path()

    # 解析播放列表
    playlist_file = Path(__file__).parent / "playlist_new.txt"
    videos = parse_playlist(playlist_file)

    print(f"📹 播放列表共 {len(videos)} 个视频")
    print(f"📁 工作目录: {cwd}")
    print(f"📁 输出目录: {output_dir}\n")

    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "transcripts").mkdir(exist_ok=True)
    (output_dir / "notes").mkdir(exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)

    # 处理每个视频
    success_count = 0
    failed_videos = []

    for i, video in enumerate(videos, start=1):
        if process_video(i, video, config_path, output_dir, video_dir):
            success_count += 1
            save_progress(i, len(videos), video['title'], output_dir)
        else:
            failed_videos.append(f"{i}. {video['title']}")

    # 生成总结
    print(f"\n{'='*60}")
    print(f"✅ 处理完成!")
    print(f"{'='*60}")
    print(f"成功: {success_count}/{len(videos)}")

    if failed_videos:
        print(f"\n❌ 失败的视频 ({len(failed_videos)}):")
        for video in failed_videos:
            print(f"   - {video}")

    # 生成思维导图
    if success_count > 0:
        print(f"\n🧠 生成思维导图...")
        from generate_mindmap import generate_mindmap
        try:
            mindmap = generate_mindmap(config_path, str(output_dir / "notes"))
            mindmap_file = output_dir / "notes" / "00_思维导图.md"
            with open(mindmap_file, 'w', encoding='utf-8') as f:
                f.write(mindmap)
            print(f"✅ 思维导图已生成: {mindmap_file.name}")
        except Exception as e:
            print(f"⚠️ 思维导图生成失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
