#!/usr/bin/env python3
"""AI社媒信息采集脚本 —— V2EX / Reddit / TechCrunch / 少数派"""

import re
import json
import sys
import time
import subprocess
import html as html_module
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
TIMEOUT = 20
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


def detect_system_proxy():
    """自动检测 macOS 系统代理设置 (scutil --proxy)"""
    try:
        result = subprocess.run(["scutil", "--proxy"], capture_output=True, text=True, timeout=5)
        host = port = None
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line.startswith("HTTPProxy"):
                host = line.split(":")[-1].strip()
            elif line.startswith("HTTPPort"):
                port = line.split(":")[-1].strip()
        if host and port:
            proxy = f"http://{host}:{port}"
            print(f"  -> 检测到系统代理: {proxy}", file=sys.stderr)
            return proxy
    except Exception:
        pass
    return None


def fetch_with_proxy(url, proxy_url):
    """通过指定代理发起请求"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                          proxies={"http": proxy_url, "https": proxy_url})
        resp.encoding = "utf-8"
        return resp.text if resp.status_code == 200 else None
    except Exception as e:
        print(f"  -> 代理请求异常: {url} - {e}", file=sys.stderr)
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
    except:
        pass
    return None


def in_range(d):
    return d is not None and YESTERDAY <= d <= TODAY


# -------- 社媒采集器 --------

def parse_v2ex(html):
    """V2EX /go/ai 帖子列表"""
    soup = BeautifulSoup(html, "html.parser")
    posts = []
    for item in soup.select("span.item_title"):
        a = item.find("a")
        if not a:
            continue
        href = a.get("href", "")
        title = a.get_text(strip=True)
        cell = item.find_parent("div", class_="cell")
        replies = cell.select_one("a.count_livid").get_text(strip=True) if cell and cell.select_one("a.count_livid") else "0"
        posts.append({
            "title": title, "link": f"https://www.v2ex.com{href}",
            "replies": replies, "date": "", "source": "V2EX",
        })
    return posts


def parse_reddit(data):
    """Reddit r/artificial JSON API"""
    import datetime as dt
    posts = []
    try:
        children = json.loads(data)["data"]["children"]
    except:
        return posts
    for child in children:
        d = child.get("data", {})
        title = d.get("title", "")
        permalink = d.get("permalink", "")
        score = d.get("score", 0)
        comments = d.get("num_comments", 0)
        created = d.get("created_utc", 0)
        post_date = dt.datetime.fromtimestamp(created).date()
        posts.append({
            "title": title,
            "link": f"https://reddit.com{permalink}",
            "score": score, "comments": comments,
            "date": str(post_date), "source": "Reddit",
        })
    return posts


def parse_old_reddit_html(html):
    """从 old.reddit.com HTML 解析帖子列表（JSON API 不通时的 fallback）"""
    posts = []
    for m in re.finditer(
        r'<div[^>]*id="thing_t3_([^"]+)"[^>]*data-permalink="([^"]+)"[^>]*data-domain="([^"]*)"[^>]*>',
        html
    ):
        permalink = m.group(2)
        remaining = html[m.end():m.end()+3000]
        title_match = re.search(r'<a[^>]*class="[^"]*may-blank[^"]*"[^>]*>([^<]+)</a>', remaining)
        title = html_module.unescape(title_match.group(1).strip()) if title_match else "N/A"
        score_match = re.search(r'<div[^>]*class="[^"]*score[^"]*unvoted[^"]*"[^>]*>([0-9]+)</div>', remaining)
        score = int(score_match.group(1)) if score_match else 0
        comments_match = re.search(r'<a[^>]*>(\d+)\s*comment', remaining)
        comments = int(comments_match.group(1)) if comments_match else 0
        posts.append({
            "title": title,
            "link": f"https://www.reddit.com{permalink}",
            "score": score,
            "comments": comments,
            "date": "",
            "source": "Reddit",
        })
    return posts


def parse_rss(html):
    """通用 RSS 解析"""
    f = feedparser.parse(html)
    articles = []
    for entry in f.entries:
        title = entry.get("title", "")
        link = entry.get("link", "")
        pub = entry.get("published", "")
        summary = re.sub(r"<[^>]+>", "", entry.get("summary", "") or "").strip()[:200]
        articles.append({
            "title": title, "link": link, "summary": summary,
            "date": pub, "source": "RSS",
        })
    return articles


# -------- 评论采集 --------

def fetch_reddit_comments(permalink, max_comments=5):
    """取 Reddit 帖子评论"""
    url = f"https://www.reddit.com{permalink}.json?limit={max_comments}"
    html_or_json = fetch(url)
    if not html_or_json:
        return []
    try:
        data = json.loads(html_or_json)
        comments = data[1]["data"]["children"]
    except:
        return []
    results = []
    for c in comments[:max_comments]:
        if c["kind"] != "t1":
            continue
        d = c["data"]
        body = d.get("body", "")[:200]
        score = d.get("score", 0)
        if body:
            results.append({"body": body, "score": score})
    return results


def fetch_v2ex_replies(tid, max_replies=5):
    """取 V2EX 帖子回复"""
    url = f"https://www.v2ex.com/t/{tid}"
    html = fetch(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for alt in soup.select("td.alt"):
        # 找回复内容
        reply_content = alt.find_next("div", class_="reply_content")
        if reply_content:
            text = reply_content.get_text(strip=True)[:200]
            if text:
                results.append({"body": text})
    return results[:max_replies]


# -------- 主流程 --------

# HN AI 关键词过滤
HN_AI_KEYWORDS = ['ai', 'llm', 'gpt', 'claude', 'openai', 'anthropic', 'gemini', 'copilot',
                   'machine learning', 'deep learning', 'neural', 'transformer', 'agent',
                   'chatbot', 'rag', 'fine.tun', 'reasoning', ' hallucinat']


def parse_hn_rss(html):
    """Hacker News RSS → 过滤出 AI 相关帖子"""
    f = feedparser.parse(html)
    items = []
    for entry in f.entries:
        title = entry.get("title", "")
        link = entry.get("link", "")
        pub = entry.get("published", "")
        comments_url = entry.get("comments", "")
        item_id = ""
        if comments_url:
            m = re.search(r'id=(\d+)', comments_url)
            if m:
                item_id = m.group(1)
        title_lower = title.lower()
        if any(kw in title_lower for kw in HN_AI_KEYWORDS):
            items.append({
                "title": title, "link": link, "date": pub,
                "source": "Hacker News", "item_id": item_id,
                "hn_discussion": comments_url,
            })
    return items


def fetch_hn_comments(item_id):
    """取 HN 帖子评论（通过 API）"""
    url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
    data = fetch(url)
    if not data:
        return []
    try:
        import json
        item = json.loads(data)
        kids = item.get("kids", [])[:5]
    except:
        return []
    results = []
    for kid_id in kids:
        c = fetch(f"https://hacker-news.firebaseio.com/v0/item/{kid_id}.json")
        if c:
            try:
                cdata = json.loads(c)
                body = cdata.get("text", "")[:200]
                score = cdata.get("score", 0)
                body = re.sub(r'<[^>]+>', '', body).strip()
                if body:
                    results.append({"body": body, "score": score})
            except:
                pass
    return results


SOURCES = [
    {"name": "V2EX /go/ai",       "url": "https://www.v2ex.com/go/ai",              "parser": parse_v2ex},
    {"name": "Reddit r/artificial","url": "https://www.reddit.com/r/artificial/.json","parser": parse_reddit},
    {"name": "Reddit r/singularity","url": "https://www.reddit.com/r/singularity/.json","parser": parse_reddit},
    {"name": "Hacker News",       "url": "https://news.ycombinator.com/rss",         "parser": parse_hn_rss},
    {"name": "TechCrunch AI",     "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "parser": parse_rss},
    {"name": "少数派",           "url": "https://sspai.com/feed",                  "parser": parse_rss},
]
SITE_NAMES = [s["name"] for s in SOURCES]


def fetch_post_content(link):
    """获取帖子/文章正文，供 Claude 分析"""
    html = fetch(link)
    if not html:
        return ""
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    texts = []
    for m in re.finditer(r'>([^<]{40,})<', html):
        t = html_module.unescape(m.group(1).strip())
        t = re.sub(r'\s+', ' ', t)
        if any(skip in t for skip in ['{', 'function', 'const ', 'var ', 'class=\"', 'menu', 'footer']):
            continue
        if t not in texts:
            texts.append(t)
    result = '\n\n'.join(texts)
    return result[:6000] if len(result) > 100 else ""


def format_output(result):
    today_s = TODAY.strftime("%Y年%-m月%-d日")
    yest_s = YESTERDAY.strftime("%Y年%-m月%-d日")
    lines = [f"# AI 社媒讨论动态（{yest_s} - {today_s}）\n"]
    for name in SITE_NAMES:
        data = result.get(name, {})
        lines.append("---\n")
        lines.append(f"## {name}\n")
        if data.get("status") != "ok":
            lines.append("暂无更新\n")
            continue
        items = data.get("items", [])
        if not items:
            lines.append("暂无更新\n")
            continue
        for i, item in enumerate(items[:5], 1):
            title = item.get("title", "")
            link = item.get("link", "")
            meta = []
            if "score" in item:
                meta.append(f"👍{item['score']}")
            if "comments" in item:
                meta.append(f"💬{item['comments']}")
            if "replies" in item:
                meta.append(f"💬{item['replies']}")
            if "summary" in item and item["summary"]:
                meta.append(item["summary"][:60])
            meta_str = f" ({' '.join(meta)})" if meta else ""
            lines.append(f"**{i}. {title}**{meta_str}")
            if link:
                lines.append(link)
            lines.append("")
        total = data.get("total", 0)
        if total:
            lines.append(f"> 共 {total} 条\n")
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AI社媒信息采集")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    proxy_url = None
    result = {}
    for src in SOURCES:
        print(f"采集: {src['name']} ({src['url']})", file=sys.stderr)
        html = fetch(src["url"])
        parser = src["parser"]

        # Reddit fallback: JSON API 不通时改用 old.reddit.com HTML
        is_reddit = src["name"].startswith("Reddit")
        if not html and is_reddit:
            sub_name = src["url"].split("/r/")[1].split(".")[0]
            alt_url = f"https://old.reddit.com/r/{sub_name}/"
            proxy_url = detect_system_proxy()
            if proxy_url:
                print(f"  -> JSON API 不可达，尝试 old.reddit.com (代理)", file=sys.stderr)
                html = fetch_with_proxy(alt_url, proxy_url)
                if html:
                    parser = parse_old_reddit_html

        if not html:
            result[src["name"]] = {"status": "error", "items": []}
            print("  -> 失败", file=sys.stderr)
            continue
        items = parser(html)

        # 过滤时间窗口（V2EX / old.reddit fallback 无日期字段，跳过过滤）
        skip_date_filter = (
            src["name"] == "V2EX /go/ai" or
            parser == parse_old_reddit_html
        )
        if skip_date_filter:
            recent = items
        else:
            recent = [i for i in items if in_range(parse_date(i.get("date", "")))]
        recent.sort(key=lambda x: parse_date(x.get("date", "")) or date.min, reverse=True)

        # 补充正文（Reddit fallback 也用代理）
        for i in recent[:5]:
            if i.get("link"):
                if is_reddit and proxy_url:
                    i["content"] = fetch_with_proxy(i["link"], proxy_url) or ""
                    time.sleep(0.5)
                else:
                    i["content"] = fetch_post_content(i["link"])
                    time.sleep(0.5)

        # Reddit 评论（fallback 时也走代理，但 JSON API 可能 403，静默跳过）
        for i in recent[:3]:
            if i.get("source") == "Reddit" and i.get("link"):
                import urllib.parse
                permalink = urllib.parse.urlparse(i["link"]).path
                if proxy_url:
                    comments_data = fetch_with_proxy(f"https://www.reddit.com{permalink}.json", proxy_url)
                    if comments_data:
                        try:
                            cdata = json.loads(comments_data)
                            i["comments_detail"] = [
                                {"body": c["data"].get("body", "")[:200], "score": c["data"].get("score", 0)}
                                for c in cdata[1]["data"]["children"][:5] if c["kind"] == "t1"
                            ]
                        except:
                            pass
                else:
                    i["comments_detail"] = fetch_reddit_comments(permalink)
                time.sleep(0.3)

        # HN 取评论
        for i in recent[:3]:
            if i.get("source") == "Hacker News" and i.get("item_id"):
                i["comments_detail"] = fetch_hn_comments(i["item_id"])
                time.sleep(0.3)

        result[src["name"]] = {"status": "ok", "items": recent, "total": len(items)}
        print(f"  -> 近两日 {len(recent)} / 共 {len(items)}", file=sys.stderr)

    if args.format == "markdown":
        print(format_output(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
