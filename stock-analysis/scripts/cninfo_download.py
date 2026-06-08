#!/usr/bin/env python3
"""
A股申报文件下载工具（巨潮资讯 API）

通过巨潮资讯网 (cninfo.com.cn) 获取 A 股公司年报、季报、半年度报告全文 PDF，
以及投资者关系活动记录（替代电话会纪要），并用 pypdf 提取为纯文本。

用法：
  python3 cninfo_download.py <STOCK_CODE> [--type 年报|季报|半年度报告|电话会] [--count N] [--output DIR]

示例：
  python3 cninfo_download.py 300308                         # 最新年报
  python3 cninfo_download.py 600519 --type 季报              # 最新季报
  python3 cninfo_download.py 000568 --type 半年度报告        # 最新中报
  python3 cninfo_download.py 002594 --type 电话会 --count 3  # 最近3份投资者关系活动记录
  python3 cninfo_download.py 300308 --type 年报 --output stock-analysis/博通/source_docs/

原理：
  1. szse_stock.json → orgId
  2. 查询公告列表（不加 category 过滤！避免返回摘要而非全文）
  3. 筛选标题（含"年度报告"/"季度报告"/"半年度报告"/"投资者关系活动记录"，不含"摘要""提示"）
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

# 类型别名 → cninfo 标题关键字
REPORT_TYPES = {
    "年报": "年度报告",
    "季报": "季度报告",
    "半年度报告": "半年度报告",
    "电话会": "投资者关系活动记录",
}

# cninfo 标题关键字 → 输出文件名前缀
CN_PREFIX = {
    "年度报告": "年报",
    "季度报告": "季报",
    "半年度报告": "季报",
    "投资者关系活动记录": "电话会纪要",
}


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
    年报/季报/半年度报告：不加 searchkey，用标题筛选。
    投资者关系活动记录：加 searchkey 精确搜索。
    """
    url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
    today = __import__("datetime").date.today()
    date_range = f"{today.year - 6}-01-01~{today.year + 1}-12-31"
    params = {
        "pageNum": 1, "pageSize": page_size,
        "stock": f"{stock_code},{org_id}",
        "seDate": date_range,
    }
    # 投资者关系活动记录使用 searchkey 精确搜索
    if keyword == "投资者关系活动记录":
        params["searchkey"] = keyword
    data = urllib.parse.urlencode(params).encode()
    result = json.loads(_req(url, data=data).read())
    return result.get("announcements", [])


def find_pdfs(announcements, keyword):
    """
    从公告列表中筛选目标 PDF 列表。
    筛选规则：标题含 keyword，不含"摘要""提示"等。
    返回 [(pdf_url, date_str, title), ...]
    """
    results = []
    for item in announcements:
        title = item.get("announcementTitle", "")
        if keyword not in title:
            continue
        if "摘要" in title or "提示" in title:
            continue
        adjunct_url = item.get("adjunctUrl", "")
        if not adjunct_url:
            continue
        pdf_url = "http://static.cninfo.com.cn/" + adjunct_url.lstrip("/")
        # 优先从标题提取日期（如"2026年5月12日投资者关系活动记录表"）
        date_str = "unknown"
        cn_match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", title)
        if cn_match:
            y, m, d = cn_match.groups()
            date_str = f"{y}{int(m):02d}{int(d):02d}"
        else:
            ts = item.get("announcementTime")
            if ts:
                ts_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(ts))
                if ts_match:
                    date_str = "".join(ts_match.groups())
        results.append((pdf_url, date_str, title))
    results.sort(key=lambda x: x[1], reverse=True)
    return results


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
                        help="文件类型：年报 / 季报 / 半年度报告 / 电话会（默认年报）")
    parser.add_argument("--count", "-n", type=int, default=1,
                        help="下载份数（默认 1，仅电话会有效，其他类型始终只取最新 1 份）")
    parser.add_argument("--output", "-o", default=".",
                        help="输出目录（默认当前目录）")
    args = parser.parse_args()

    original_type = args.type
    keyword = REPORT_TYPES.get(args.type, args.type)
    prefix = CN_PREFIX.get(keyword, keyword)

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

    # 3. 找到 PDF 列表
    pdf_list = find_pdfs(announcements, keyword)
    if not pdf_list:
        print(f"❌ 未找到 {keyword} 全文PDF（可能只有摘要版）")
        sys.exit(1)

    # 如果是年报/季报类型，只取最新一份；电话会取前 args.count 份
    if original_type != "电话会":
        pdf_list = pdf_list[:1]
    else:
        pdf_list = pdf_list[:args.count]

    print(f"✅ 匹配到 {len(pdf_list)} 份文档")

    # 4. 逐个下载 + 提取
    os.makedirs(args.output, exist_ok=True)
    success = 0
    for pdf_url, date_str, title in pdf_list:
        print(f"\n⏳ [{success+1}/{len(pdf_list)}] {title}...")
        try:
            text, total_pages = download_and_extract(pdf_url)
        except Exception as e:
            print(f"   ❌ 下载/提取失败: {e}")
            continue

        filename = f"{prefix}_{date_str}.txt"
        output = os.path.join(args.output, filename)
        with open(output, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"   ✅ {filename} ({total_pages} 页, {len(text)/1024/1024:.1f} MB)")
        success += 1

    if success > 0:
        print(f"\n📁 共 {success} 份文件已保存到 {args.output}/")
    else:
        print("\n❌ 所有文件下载均失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
