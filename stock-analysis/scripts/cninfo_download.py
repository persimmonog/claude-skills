#!/usr/bin/env python3
"""
A股申报文件下载工具（巨潮资讯 API）

通过巨潮资讯网 (cninfo.com.cn) 获取 A 股公司年报、季报、半年度报告全文 PDF，
并用 pypdf 提取为纯文本。

用法：
  python3 cninfo_download.py <STOCK_CODE> [--type 年报|季报|半年度报告] [--output DIR]

示例：
  python3 cninfo_download.py 300308                         # 最新年报
  python3 cninfo_download.py 600519 --type 季报              # 最新季报
  python3 cninfo_download.py 000568 --type 半年度报告        # 最新中报
  python3 cninfo_download.py 300308 --type 年报 --output stock-analysis/博通/source_docs/

原理：
  1. szse_stock.json → orgId
  2. 查询公告列表（不加 category 过滤！避免返回摘要而非全文）
  3. 筛选标题（含"年度报告"/"季度报告"/"半年度报告"，不含"摘要""提示"）
  4. 下载 PDF → pypdf 提取纯文本

⚠️ 关键：不要加 category_ndbg_szsh 等过滤参数，否则只返回摘要不返回全文！
"""

import argparse
import io
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
from pypdf import PdfReader

PYPI_SOURCES = {"年报": "年度报告", "季报": "季度报告", "半年度报告": "半年度报告"}


def _ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _req(url, data=None, timeout=20):
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, data=data, headers=headers)
    return urllib.request.urlopen(req, timeout=timeout, context=_ctx())


def get_org_id(stock_code):
    """从 szse_stock.json 获取 orgId"""
    resp = _req("http://www.cninfo.com.cn/new/data/szse_stock.json")
    for item in json.loads(resp.read())["stockList"]:
        if item["code"] == stock_code:
            return item["orgId"]
    raise ValueError(f"未找到股票代码 {stock_code} 的 orgId")


def search_announcements(org_id, stock_code, keyword, page_size=30):
    """
    查询公告列表。
    ⚠️ 不加 category 过滤参数——category_ndbg_szsh 等只返回摘要不返回全文。
    """
    url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
    today = __import__("datetime").date.today()
    date_range = f"{today.year - 6}-01-01~{today.year + 1}-12-31"
    data = urllib.parse.urlencode({
        "pageNum": 1, "pageSize": page_size,
        "stock": f"{stock_code},{org_id}",
        "seDate": date_range,
    }).encode()
    result = json.loads(_req(url, data=data).read())
    return result.get("announcements", [])


def find_pdf(announcements, keyword):
    """
    从公告列表中筛选目标 PDF。
    筛选规则：标题含 keyword（如"年度报告"），不含"摘要""提示"等。
    """
    for item in announcements:
        title = item.get("announcementTitle", "")
        if keyword in title and "摘要" not in title and "提示" not in title:
            adjunct_url = item.get("adjunctUrl", "")
            if adjunct_url:
                pdf_url = "http://static.cninfo.com.cn/" + adjunct_url.lstrip("/")
                # 从标题提取日期
                date_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", item.get("announcementDate", ""))
                date_str = "".join(date_match.groups()) if date_match else "unknown"
                return pdf_url, date_str
    return None, None


def download_and_extract(pdf_url):
    """下载 PDF 并用 pypdf 提取纯文本"""
    data = _req(pdf_url, timeout=30).read()
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages), len(reader.pages)


def main():
    parser = argparse.ArgumentParser(description="A股申报文件下载（巨潮资讯）")
    parser.add_argument("stock_code", help="A股股票代码，如 300308、600519")
    parser.add_argument("--type", default="年报",
                        help="文件类型：年报 / 季报 / 半年度报告（默认年报）")
    parser.add_argument("--output", "-o", default=".",
                        help="输出目录（默认当前目录）")
    args = parser.parse_args()

    keyword = PYPI_SOURCES.get(args.type, args.type)
    print(f"🔍 正在搜索 {args.stock_code} 的{keyword}...")

    # 1. 获取 orgId
    try:
        org_id = get_org_id(args.stock_code)
        print(f"✅ orgId: {org_id}")
    except Exception as e:
        print(f"❌ 获取 orgId 失败: {e}")
        sys.exit(1)

    # 2. 搜索公告
    announcements = search_announcements(org_id, args.stock_code, keyword)
    print(f"✅ 找到 {len(announcements)} 条公告")

    # 3. 找到 PDF
    pdf_url, date_str = find_pdf(announcements, keyword)
    if not pdf_url:
        print(f"❌ 未找到 {keyword} 全文PDF（可能只有摘要版）")
        sys.exit(1)
    print(f"✅ 找到 PDF: {pdf_url}")

    # 4. 下载 + 提取
    print(f"⏳ 正在下载并提取文本...")
    try:
        text, total_pages = download_and_extract(pdf_url)
    except Exception as e:
        print(f"❌ 下载/提取失败: {e}")
        sys.exit(1)

    cn_type = {"年度报告": "年报", "季度报告": "季报", "半年度报告": "季报"}.get(keyword, keyword)
    filename = f"{cn_type}_{date_str}.txt"
    output = os.path.join(args.output, filename)
    os.makedirs(args.output, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"✅ {filename} ({total_pages} 页, {len(text)/1024/1024:.1f} MB)")
    print(f"📁 已保存到 {output}")


if __name__ == "__main__":
    main()
