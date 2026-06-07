#!/usr/bin/env python3
"""
美股 SEC 申报文件下载工具（基于 sec-edgar-downloader）

从 SEC EDGAR 下载美股申报文件全文（10-K/10-Q/DEF 14A/8-K 等），
自动按"中文类型_YYYYMMDD.txt"规范命名。

用法：
  python3 sec_filing.py <TICKER> <FORM> [--count N] [--output DIR]

示例：
  python3 sec_filing.py AVGO 10-K              # 年报
  python3 sec_filing.py AVGO 10-Q --count 4    # 最近4份季报
  python3 sec_filing.py AVGO DEF14A            # 委托书
  python3 sec_filing.py AVGO 8-K               # 重大事件
  python3 sec_filing.py AAPL 10-K              # 其他公司的年报

依赖（首次运行自动安装）：
  pip3 install sec-edgar-downloader -q
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

# ── 申报类型 → 中文文件名前缀 ──
FORM_CN = {
    "10-K": "年报",
    "10-Q": "季报",
    "DEF 14A": "委托书",
    "DEF14A": "委托书",
    "8-K": "重大事件",
    "S-1": "招股书",
    "F-1": "招股书",
    "20-F": "年报",
    "6-K": "季报",
    "SD": "特别披露",
    "13G": "股东申报",
    "13D": "股东申报",
}

FORM_INPUT_MAP = {"DEF14A": "DEF 14A"}


def ensure_deps():
    """确保 sec-edgar-downloader 已安装"""
    try:
        from sec_edgar_downloader import Downloader
        return Downloader
    except ImportError:
        print("📦 安装 sec-edgar-downloader...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "sec-edgar-downloader", "-q"]
        )
        from sec_edgar_downloader import Downloader
        return Downloader


def extract_date_from_header(txt_path, form):
    """
    从 SEC full-submission.txt 的头部提取日期。

    规则：
      - 10-Q → CONFORMED PERIOD OF REPORT（季末日期）
      - 10-K → CONFORMED PERIOD OF REPORT（财年末日期）
      - 其他 → FILED AS OF DATE（提交日期）
    """
    with open(txt_path, "r", errors="replace") as f:
        header = f.read(2000)

    # 解析关键字段
    report = re.search(r"CONFORMED PERIOD OF REPORT:\s+(\d{4})(\d{2})(\d{2})", header)
    filed = re.search(r"FILED AS OF DATE:\s+(\d{4})(\d{2})(\d{2})", header)

    if form in ("10-K", "10-Q") and report:
        return report.group(1) + report.group(2) + report.group(3)
    elif filed:
        return filed.group(1) + filed.group(2) + filed.group(3)
    elif report:
        return report.group(1) + report.group(2) + report.group(3)
    else:
        # 从 accession number 推断年份
        acc_match = re.search(r"ACCESSION NUMBER:\s+(\d{10})-(\d{2})-(\d{6})", header)
        if acc_match:
            yy = acc_match.group(2)
            year = "20" + yy if int(yy) < 90 else "19" + yy
            return year + "0101"
        return "unknown"


def main():
    parser = argparse.ArgumentParser(
        description="从 SEC EDGAR 下载美股申报文件全文（基于 sec-edgar-downloader）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python3 sec_filing.py AVGO 10-K              # 最新年报\n"
            "  python3 sec_filing.py AVGO 10-Q --count 4    # 最近4份季报\n"
            "  python3 sec_filing.py AVGO DEF14A            # 委托书\n"
            "  python3 sec_filing.py AAPL 10-K --count 2    # 最近2份年报\n"
        ),
    )
    parser.add_argument("ticker", help="股票代码，如 AVGO、AAPL、MSFT")
    parser.add_argument("form", help="申报类型: 10-K, 10-Q, DEF14A, 8-K, S-1 等")
    parser.add_argument("--count", "-n", type=int, default=1, help="下载份数（默认 1）")
    parser.add_argument("--output", "-o", default=".", help="输出目录（默认当前目录）")
    args = parser.parse_args()

    form_search = FORM_INPUT_MAP.get(args.form, args.form)
    cn_prefix = FORM_CN.get(form_search, form_search)
    ticker = args.ticker.upper()

    # 1. 初始化下载器
    Downloader = ensure_deps()
    tmp_dir = tempfile.mkdtemp(prefix="sec_filing_")
    dl = Downloader("StockAnalysisBot", "stock-analysis@local", download_folder=tmp_dir)

    print(f"🔍 正在下载 {ticker} 的 {form_search}（最近 {args.count} 份）...")

    try:
        n = dl.get(form_search, ticker, limit=args.count)
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        sys.exit(1)

    if n == 0:
        print(f"❌ 未找到 {form_search} 类型的申报文件")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        sys.exit(1)

    print(f"✅ 成功下载 {n} 份\n")

    # 2. 遍历下载目录，提取到输出目录
    base = os.path.join(tmp_dir, "sec-edgar-filings", ticker, form_search)
    count = 0
    if os.path.isdir(base):
        for acc in sorted(os.listdir(base), reverse=True)[: args.count]:
            src = os.path.join(base, acc, "full-submission.txt")
            if not os.path.isfile(src):
                continue
            date_str = extract_date_from_header(src, form_search)
            filename = f"{cn_prefix}_{date_str}.txt"
            dst = os.path.join(args.output, filename)
            os.makedirs(args.output, exist_ok=True)
            shutil.copy2(src, dst)
            size_mb = os.path.getsize(dst) / 1024 / 1024
            print(f"  [{count+1}/{n}] {filename}  ({size_mb:.1f} MB)")
            count += 1

    # 3. 清理临时目录
    shutil.rmtree(tmp_dir, ignore_errors=True)

    if count == 0:
        print("⚠️  未找到任何已下载的文件（可能保存位置异常）")
        sys.exit(1)

    print(f"\n📁 文件已保存到 {args.output}/")


if __name__ == "__main__":
    main()
