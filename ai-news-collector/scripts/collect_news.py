#!/usr/bin/env python3
"""AI头部公司博客信息采集脚本"""

import re
import json
import sys
import time
import html as html_module
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TIMEOUT = 25

DATE_FORMATS = [
    "%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y",
    "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%b %-d, %Y", "%Y年%m月%d日",
]


def fetch(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.encoding = "utf-8"
        return resp.text if resp.status_code == 200 else None
    except Exception as e:
        print(f"  -> 请求异常: {url} - {e}", file=sys.stderr)
        return None


def parse_date(date_str):
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).date()
        except (ValueError, TypeError):
            continue
    try:
        return datetime.fromisoformat(date_str).date()
    except (ValueError, TypeError, AttributeError):
        pass
    return None


def in_range(d):
    return d is not None and YESTERDAY <= d <= TODAY


# -------- RSS 统一解析 --------

def parse_rss(html):
    """通用 RSS/Atom 解析"""
    f = feedparser.parse(html)
    articles = []
    seen = set()
    for entry in f.entries:
        link = entry.get("link", "")
        title = entry.get("title", "")
        pub = entry.get("published", "")
        summary = entry.get("summary", "") or entry.get("description", "")
        summary = html_module.unescape(re.sub(r"<[^>]+>", "", summary).strip())
        if link and link not in seen:
            seen.add(link)
            articles.append({"title": title, "summary": summary, "link": link, "date": pub})
    return articles


# -------- HTML 统一解析 --------

def parse_anthropic_news(html):
    """Anthropic News"""
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    seen = set()
    for item in soup.select("li"):
        date_el = item.find(class_=re.compile(r"date"))
        title_el = item.find(class_=re.compile(r"title"))
        link_el = item.find("a")
        if title_el:
            title = title_el.get_text(strip=True)
            link = f"https://anthropic.com{link_el['href']}" if link_el and link_el.get("href") else ""
            if link in seen:
                continue
            seen.add(link)
            articles.append({
                "title": title, "summary": "", "link": link,
                "date": date_el.get_text(strip=True) if date_el else ""
            })
    # Featured grid
    featured = soup.find(class_=re.compile(r"FeaturedGrid"))
    if featured:
        for item in featured.find_all(class_=re.compile(r"title")):
            link_el = item.find_parent("a")
            date_el = featured.find(class_=re.compile(r"date"))
            title = item.get_text(strip=True)
            link = f"https://anthropic.com{link_el['href']}" if link_el and link_el.get("href") else ""
            if link in seen:
                continue
            seen.add(link)
            articles.append({
                "title": title, "summary": "", "link": link,
                "date": date_el.get_text(strip=True) if date_el else ""
            })
    for a in articles[:5]:
        if not a["summary"]:
            a["summary"] = _fetch_summary(a["link"])
            time.sleep(0.3)
    return articles


def parse_anthropic_research(html):
    """Anthropic Research"""
    links = re.findall(r'href="(/research/[^"]+)"', html)
    seen = set()
    articles = []
    for link_path in links:
        if "/team/" in link_path:
            continue
        full = f"https://anthropic.com{link_path}"
        if full not in seen:
            seen.add(full)
            articles.append({"title": "", "summary": "", "link": full, "date": ""})

    # 配对日期
    dates = [(m.start(), m.group(1)) for m in re.finditer(r'([A-Z][a-z]+ \d{1,2}, \d{4})', html)]
    link_pos = [(m.start(), m.group(1)) for m in
                re.finditer(r'href="(/research/[^"/]+(?!/team)[^"]*)"', html)]
    for dpos, dstr in dates:
        for lpos, lpath in link_pos:
            if lpos > dpos:
                for a in articles:
                    if a["link"] == f"https://anthropic.com{lpath}" and not a["date"]:
                        a["date"] = dstr
                break

    recent = [a for a in articles if in_range(parse_date(a.get("date", "")))]
    return recent


def parse_html_cards(soup, container, title_sel, link_prefix, link_attr="href",
                     summary_sel=None, date_pattern=None, link_filter=None, min_title=0):
    """通用 HTML 卡片解析器——适用于 <a> 标签包裹整张卡片的站点"""
    articles = []
    seen = set()
    for card in soup.select(container):
        href = card.get(link_attr, "")
        if link_filter and not link_filter(href):
            continue
        if href in seen:
            continue
        seen.add(href)
        title_el = card.find(title_sel) if isinstance(title_sel, str) else card.find(title_sel[0])
        title = title_el.get_text(strip=True) if title_el else ""
        if len(title) < min_title:
            continue
        summary = ""
        if summary_sel:
            s = card.select_one(summary_sel) if isinstance(summary_sel, str) else card.find(summary_sel)
            summary = s.get_text(strip=True) if s else ""
        date_str = ""
        if date_pattern:
            m = re.search(date_pattern, card.get_text())
            date_str = m.group(1) if m else ""
        articles.append({
            "title": title, "summary": summary,
            "link": f"{link_prefix}{href}", "date": date_str
        })
    return articles


def parse_anthropic_news(html):
    """Anthropic News"""
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    seen = set()
    for item in soup.select("li"):
        date_el = item.find(class_=re.compile(r"date"))
        title_el = item.find(class_=re.compile(r"title"))
        link_el = item.find("a")
        if title_el:
            title = title_el.get_text(strip=True)
            link = f"https://anthropic.com{link_el['href']}" if link_el and link_el.get("href") else ""
            if link in seen:
                continue
            seen.add(link)
            articles.append({
                "title": title, "summary": "", "link": link,
                "date": date_el.get_text(strip=True) if date_el else ""
            })
    featured = soup.find(class_=re.compile(r"FeaturedGrid"))
    if featured:
        for item in featured.find_all(class_=re.compile(r"title")):
            link_el = item.find_parent("a")
            title = item.get_text(strip=True)
            link = f"https://anthropic.com{link_el['href']}" if link_el and link_el.get("href") else ""
            if link in seen:
                continue
            seen.add(link)
            articles.append({
                "title": title, "summary": "", "link": link, "date": ""
            })
    return articles


def parse_nous(html):
    """Nous Research"""
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    seen = set()
    for a in soup.select('a[href^="/"]'):
        href = a["href"]
        if any(e in href for e in ["wp-", "elementor", ".css", ".js", "#"]):
            continue
        full = f"https://nousresearch.com{href}"
        if full in seen:
            continue
        seen.add(full)
        title_el = a.find(class_=re.compile(r"heading-title"))
        title = title_el.get_text(strip=True) if title_el else ""
        if len(title) < 15:
            continue
        articles.append({"title": title, "summary": "", "link": full, "date": ""})
    return articles


def parse_xai(html):
    """xAI News"""
    soup = BeautifulSoup(html, "html.parser")
    articles = parse_html_cards(soup,
        container='a[href^="/news/"]',
        title_sel=["h1", "h2", "h3", "h4"],
        link_prefix="https://x.ai",
        summary_sel="p",
        date_pattern=r'([A-Z][a-z]+ \d{1,2}, \d{4})',
    )
    return [a for a in articles if in_range(parse_date(a.get("date", "")))]


# -------- 摘要/标题获取 --------

def _fetch_title(link, retries=2):
    for attempt in range(retries + 1):
        html = fetch(link)
        if not html:
            if attempt < retries:
                time.sleep(1)
                continue
            return ""
        m = re.search(r"<title>([^<]+)</title>", html, re.DOTALL)
        if m:
            title = m.group(1).strip()
            title = re.sub(r"\s*[\\|–-]\s*(Anthropic|OpenAI|Nous Research).*$", "", title, flags=re.I).strip()
            return title
        m = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
        if m:
            return m.group(1).strip()
        return ""
    return ""


def _fetch_content(link, retries=1):
    """获取文章正文（清洗后的纯文本），供 Claude 分析用"""
    for attempt in range(retries + 1):
        html = fetch(link)
        if not html:
            if attempt < retries:
                time.sleep(1)
                continue
            return ""
        # 去掉 script/style 标签
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        # 提取所有文本段落
        texts = []
        for m in re.finditer(r'>([^<]{40,})<', html):
            t = html_module.unescape(m.group(1).strip())
            t = re.sub(r'\s+', ' ', t)
            # 过滤导航、脚本残片等噪音
            if any(skip in t for skip in ['{', 'function', 'const ', 'var ', 'class=\"', 'href=\"', 'menu', 'footer']):
                continue
            if t not in texts:
                texts.append(t)
        # 去重后合并，最多 8000 字符
        result = '\n\n'.join(texts)
        return result[:8000] if len(result) > 100 else ""
    return ""


# -------- 数据源配置 --------

SOURCES = [
    {"name": "OpenAI",              "url": "https://openai.com/blog/rss.xml",             "parser": parse_rss},
    {"name": "Anthropic",           "url": "https://anthropic.com/news",                   "parser": parse_anthropic_news},
    {"name": "Anthropic 研究",       "url": "https://anthropic.com/research",               "parser": parse_anthropic_research},
    {"name": "Nous Research",       "url": "https://nousresearch.com/blog/",                "parser": parse_nous},
    {"name": "Hugging Face",        "url": "https://huggingface.co/blog/feed.xml",          "parser": parse_rss},
    {"name": "Google DeepMind",     "url": "https://deepmind.google/blog/rss.xml",          "parser": parse_rss},
    {"name": "Google AI",           "url": "https://blog.research.google/rss.xml",          "parser": parse_rss},
    {"name": "xAI",                 "url": "https://x.ai/news",                             "parser": parse_xai},
]

SITE_NAMES = [s["name"] for s in SOURCES]


def format_markdown(result):
    today_s = TODAY.strftime("%Y年%-m月%-d日")
    yesterday_s = YESTERDAY.strftime("%Y年%-m月%-d日")
    lines = [f"# AI 头部公司动态（{yesterday_s} - {today_s}）\n"]
    for name in SITE_NAMES:
        data = result.get(name, {})
        lines.append("---\n")
        lines.append(f"## {name}\n")
        status = data.get("status", "error")
        if status != "ok":
            lines.append("暂无更新\n" if status == "skip" else "暂无更新\n")
            continue
        articles = data.get("articles", [])
        if not articles:
            lines.append("暂无更新\n")
            continue
        total = data.get("total", 0)
        for i, a in enumerate(articles[:5], 1):
            title = html_module.unescape(a.get("title", "") or "(标题未知)")
            summary = html_module.unescape(a.get("summary", ""))
            link = a.get("link", "")
            lines.append(f"**{i}. {title}**")
            if summary:
                lines.append(summary)
            if link:
                lines.append(link)
            lines.append("")
        if total:
            lines.append(f"> 共 {total} 篇\n")
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AI头部公司博客采集")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    result = {}
    for src in SOURCES:
        print(f"采集: {src['name']} ({src['url']})", file=sys.stderr)
        html = fetch(src["url"])
        if not html:
            result[src["name"]] = {"status": "error", "articles": []}
            print("  -> 失败", file=sys.stderr)
            continue
        articles = src["parser"](html)
        recent = [a for a in articles if in_range(parse_date(a.get("date", "")))]
        recent.sort(key=lambda x: parse_date(x.get("date", "")) or date.min, reverse=True)
        for a in recent[:5]:
            if not a["title"] and a["link"]:
                a["title"] = _fetch_title(a["link"])
                time.sleep(0.3)
            # 顺便抓正文文本，Claude 直接用来写摘要，不用再 curl
            if a["link"]:
                a["content"] = _fetch_content(a["link"])
                time.sleep(0.5)
        result[src["name"]] = {"status": "ok", "articles": recent, "total": len(articles)}
        print(f"  -> 近两日 {len(recent)} / 共 {len(articles)}", file=sys.stderr)

    if args.format == "markdown":
        print(format_markdown(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
