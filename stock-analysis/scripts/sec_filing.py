#!/usr/bin/env python3
"""
美股 SEC 申报文件下载工具（ sec-edgar-downloader + 智能清洗）

从 SEC EDGAR 下载美股申报文件全文，自动提取申报文件正文
（去除 SEC 文档结构、iXBRL、附件等标签），按"中文类型_公司名_YYYYMMDD.txt"规范命名。

用法：
  python3 sec_filing.py <TICKER> --name <NAME> <FORM> [--count N] [--output DIR] [--raw]

示例：
  python3 sec_filing.py MNSO --name 名创优品 20-F                    # 年报
  python3 sec_filing.py BABA --name 阿里巴巴 20-F --count 2         # 最近2份年报
  python3 sec_filing.py AVGO --name 博通 10-Q --count 4             # 最近4份季报
  python3 sec_filing.py AVGO --name 博通 DEF14A                     # 委托书
  python3 sec_filing.py AAPL --name Apple 10-K                      # 其他公司年报
  python3 sec_filing.py MNSO --name 名创优品 6-K --count 4          # 中概股季报

依赖（首次运行自动安装）：
  pip3 install sec-edgar-downloader -q
"""

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

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

    report = re.search(r"CONFORMED PERIOD OF REPORT:\s+(\d{4})(\d{2})(\d{2})", header)
    filed = re.search(r"FILED AS OF DATE:\s+(\d{4})(\d{2})(\d{2})", header)

    if form in ("10-K", "10-Q") and report:
        return report.group(1) + report.group(2) + report.group(3)
    elif filed:
        return filed.group(1) + filed.group(2) + filed.group(3)
    elif report:
        return report.group(1) + report.group(2) + report.group(3)
    else:
        acc_match = re.search(r"ACCESSION NUMBER:\s+(\d{10})-(\d{2})-(\d{6})", header)
        if acc_match:
            yy = acc_match.group(2)
            year = "20" + yy if int(yy) < 90 else "19" + yy
            return year + "0101"
        return "unknown"


def extract_primary_text(raw_text, form):
    """
    从 full-submission.txt 中提取主申报文件正文。

    SEC full-submission.txt 的格式为一组 <DOCUMENT> 段，
    每段含 <TYPE>、<SEQUENCE>、<TEXT> 等标签。
    返回 TYPE 匹配的第一份文档的 <TEXT> 内容。
    """
    docs = re.split(r"</DOCUMENT>", raw_text)

    candidates = []
    for doc in docs:
        if not doc.strip():
            continue
        type_m = re.search(r"<TYPE>\s*(\S+)", doc, re.IGNORECASE)
        if not type_m:
            continue
        doc_type = type_m.group(1).strip()
        if doc_type.upper() != form.upper():
            continue
        seq_m = re.search(r"<SEQUENCE>\s*(\d+)", doc, re.IGNORECASE)
        seq = int(seq_m.group(1)) if seq_m else 99
        text_m = re.search(r"<TEXT>(.*?)</TEXT>", doc, re.IGNORECASE | re.DOTALL)
        if text_m:
            candidates.append((seq, text_m.group(1)))

    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    return raw_text


def collect_exhibits_text(raw_text):
    """
    收集 full-submission.txt 中所有非图片非 XBRL 文档的 TEXT 内容。
    用于 6-K/8-K 等封面页太短的情况。
    """
    docs = re.split(r"</DOCUMENT>", raw_text)
    skip_types = {"GRAPHIC", "XML", "XBRL", "EXCEL"}
    parts = []
    for doc in docs:
        type_m = re.search(r"<TYPE>\s*(\S+)", doc, re.IGNORECASE)
        if not type_m:
            continue
        dt = type_m.group(1).strip().upper()
        if dt in skip_types:
            continue
        text_m = re.search(r"<TEXT>(.*?)</TEXT>", doc, re.IGNORECASE | re.DOTALL)
        if text_m:
            parts.append(text_m.group(1))

    return "\n\n\n".join(parts) if parts else raw_text


def clean_text(content):
    """清理 HTML/XML 标签 + XBRL 噪音，提取可读文本。"""
    if not content:
        return ""

    content = content.replace("\xa0", " ")

    content = re.sub(r"<\?xml[^>]*\?>", "", content)

    # 移除 XBRL 命名空间元素（纯元数据，无可读内容）
    for ns in ["xbrli", "xbrldi", "link"]:
        content = re.sub(
            f"<{ns}:[^>]+/>", "", content, flags=re.IGNORECASE | re.DOTALL,
        )
        content = re.sub(
            f"<{ns}:[^>]+>.*?</{ns}:\\w+>", "", content,
            flags=re.IGNORECASE | re.DOTALL,
        )

    # 移除 iXBRL 纯元数据标签
    for tag in [
        "ix:hidden", "ix:resources", "ix:references",
        "ix:relationship", "ix:header", "ix:continuation",
    ]:
        content = re.sub(
            f"<{tag}[^>]*/>", "", content, flags=re.IGNORECASE | re.DOTALL,
        )
        content = re.sub(
            f"<{tag}[^>]*>.*?</{tag}>", "", content,
            flags=re.IGNORECASE | re.DOTALL,
        )

    for tag in ["HEAD", "SCRIPT", "STYLE"]:
        content = re.sub(
            f"<{tag}[^>]*>.*?</{tag}>", "", content,
            flags=re.IGNORECASE | re.DOTALL,
        )

    for tag in [
        "br", "/p", "/div", "/tr", "/li", "/h\\d", "hr",
        "/table", "/tbody", "/thead", "/tfoot",
        "/ul", "/ol", "/dl", "/dd", "/dt",
        "/blockquote", "/pre", "/section", "/article",
        "/nav", "/header", "/footer", "/aside", "/figure",
        "/caption", "/fieldset", "/details", "/summary",
    ]:
        content = re.sub(f"<{tag}[^>]*>", "\n", content, flags=re.IGNORECASE)

    content = re.sub(r"<[^>]+>", "", content)

    content = html.unescape(content)

    try:
        content = content.encode("utf-8").decode("unicode_escape")
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass

    content = re.sub(r"[ \t]+\n", "\n", content)
    content = re.sub(r"\n{4,}", "\n\n\n", content)
    content = re.sub(r" +", " ", content)

    # 过滤 XBRL 噪音行
    lines = []
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            lines.append(line)
            continue
        if len(stripped) < 200 and re.match(r"^[\s\-_=*•·]+$", stripped):
            continue
        words = stripped.split()
        if len(words) < 3:
            lines.append(line)
            continue
        ns_words = sum(1 for w in words if re.match(r"\w+:\w+", w))
        date_words = sum(1 for _ in re.findall(r"\d{4}-\d{2}-\d{2}", stripped))
        noise_ratio = (ns_words + date_words) / max(len(words), 1)
        if noise_ratio > 0.35:
            continue
        lines.append(line)

    content = "\n".join(lines)
    content = re.sub(r"\n{4,}", "\n\n\n", content)
    return content.strip()


def process_filing(src, form):
    """读取原始 full-submission.txt，提取主文档并清洗。"""
    with open(src, "r", errors="replace") as f:
        raw_text = f.read()

    doc_text = extract_primary_text(raw_text, form)

    if doc_text == raw_text:
        doc_text = collect_exhibits_text(raw_text)

    cleaned = clean_text(doc_text) if doc_text != raw_text else raw_text

    # 如果主文档太短（封面页），尝试合并所有 Exhibits
    if len(cleaned) < 5000:
        exhibit_text = collect_exhibits_text(raw_text)
        exhibit_cleaned = clean_text(exhibit_text)
        if len(exhibit_cleaned) > len(cleaned) * 3:
            cleaned = exhibit_cleaned

    return cleaned


def main():
    parser = argparse.ArgumentParser(
        description="从 SEC EDGAR 下载美股申报文件全文（sec-edgar-downloader + 智能清洗）",
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
    parser.add_argument("form", help="申报类型: 10-K, 10-Q, DEF14A, 8-K, 20-F, 6-K 等")
    parser.add_argument("--name", default=None, help="公司名称，用于文件名（默认用 ticker）")
    parser.add_argument("--count", "-n", type=int, default=1, help="下载份数（默认 1）")
    parser.add_argument("--output", "-o", default=".", help="输出目录（默认当前目录）")
    parser.add_argument("--raw", action="store_true", help="保存原始 full-submission.txt（不做清洗）")
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

    # 2. 遍历下载目录，提取并清洗
    base = os.path.join(tmp_dir, "sec-edgar-filings", ticker, form_search)
    count = 0
    if os.path.isdir(base):
        for acc in sorted(os.listdir(base), reverse=True)[: args.count]:
            src = os.path.join(base, acc, "full-submission.txt")
            if not os.path.isfile(src):
                continue

            date_str = extract_date_from_header(src, form_search)
            name_part = args.name if args.name else ticker
            filename = f"{cn_prefix}_{name_part}_{date_str}.txt"
            dst = os.path.join(args.output, filename)
            os.makedirs(args.output, exist_ok=True)

            if args.raw:
                shutil.copy2(src, dst)
                size_mb = os.path.getsize(dst) / 1024 / 1024
                print(f"  [{count+1}/{n}] {filename}  ({size_mb:.1f} MB) [RAW]")
            else:
                cleaned = process_filing(src, form_search)
                with open(dst, "w", encoding="utf-8") as f:
                    f.write(cleaned)
                size_kb = os.path.getsize(dst) / 1024
                print(f"  [{count+1}/{n}] {filename}  ({size_kb:.0f} KB)")

            count += 1

    # 3. 清理临时目录
    shutil.rmtree(tmp_dir, ignore_errors=True)

    if count == 0:
        print("⚠️  未找到任何已下载的文件（可能保存位置异常）")
        sys.exit(1)

    print(f"\n📁 文件已保存到 {args.output}/")


if __name__ == "__main__":
    main()
