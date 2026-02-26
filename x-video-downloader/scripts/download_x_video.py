#!/usr/bin/env python3
"""
X (Twitter) 视频下载脚本（支持断点续传）
使用方法：python download_x_video.py <推文链接>
示例：python download_x_video.py https://x.com/user/status/1234567890

功能特性：
- 自动下载最高质量的MP4视频
- 支持断点续传（下载中断后重新运行命令即可继续）
- 自动重试机制（最多10次）
- 显示视频信息和下载进度
- 自动下载字幕（如果有）
"""

import sys
import yt_dlp
from datetime import datetime


def download_x_video(url, output_dir='.', quality='best'):
    """
    下载X视频

    参数:
        url: X推文链接
        output_dir: 保存目录
        quality: 视频质量 (best/worst/specific format)
    """
    # 配置下载选项
    ydl_opts = {
        'outtmpl': output_dir + '/%(title)s_%(id)s.%(ext)s',
        'format': quality + '[ext=mp4]/best[ext=mp4]/best',
        'quiet': False,
        'no_warnings': False,
        'progress': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['zh-CN', 'en', 'zh-Hans'],
        # 断点续传配置
        'continue_dl': True,  # 继续未完成的下载
        'nopart': False,  # 允许使用部分文件(.part)
        'overwrites': False,  # 不覆盖已存在文件
        'fragment_retries': 10,  # 片段重试次数
        'skip_unavailable_fragments': True,  # 跳过不可用片段
        'retries': 10,  # 整体重试次数
        'file_access_retries': 5,  # 文件访问重试次数
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 获取视频信息
            info = ydl.extract_info(url, download=False)

            print("\n" + "="*60)
            print(f"标题: {info.get('title', 'N/A')}")
            print(f"作者: {info.get('uploader', 'N/A')}")
            print(f"时长: {info.get('duration', 'N/A')} 秒")
            print(f"发布时间: {info.get('upload_date', 'N/A')}")
            print("="*60 + "\n")

            # 开始下载
            print("开始下载...")
            ydl.download([url])

            print("\n✅ 下载完成！")
            return True

    except Exception as e:
        print(f"\n❌ 下载失败: {str(e)}")
        print("\n可能的原因:")
        print("1. 视频链接无效或已被删除")
        print("2. 需要登录才能访问该内容")
        print("3. 网络连接问题")
        print("\n💡 提示: 如果下载中断，直接重新运行命令即可断点续传")
        return False


def main():
    if len(sys.argv) < 2:
        print("使用方法: python download_x_video.py <X推文链接>")
        print("\n示例:")
        print("  python download_x_video.py https://x.com/user/status/1234567890")
        print("  python download_x_video.py https://twitter.com/user/status/1234567890")
        sys.exit(1)

    url = sys.argv[1]

    # 验证是否是X/Twitter链接
    if not ('x.com/' in url or 'twitter.com/' in url):
        print("❌ 错误: 请提供有效的X(Twitter)推文链接")
        sys.exit(1)

    # 可选：指定输出目录
    output_dir = '.'  # 默认当前目录
    quality = 'best'  # 默认最高质量

    download_x_video(url, output_dir, quality)


if __name__ == '__main__':
    main()
