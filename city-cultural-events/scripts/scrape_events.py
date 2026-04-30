#!/usr/bin/env python3
"""
同城文化活动数据抓取脚本
通过大麦网移动端 mtop API + DOM 解析 + 活动行 获取活动信息，输出 JSON 或 Markdown 表格格式

用法: python3 scrape_events.py <城市> [活动类型] [数量] [--format json|markdown]
示例: python3 scrape_events.py 北京
      python3 scrape_events.py 上海 展览 20
      python3 scrape_events.py 广州 --format markdown
"""

import asyncio
import json
import re
import sys
from datetime import datetime
from playwright.async_api import async_playwright


async def scrape_damai(city, event_type="全部", max_items=20):
    """
    通过 Playwright 打开大麦首页，结合 API 拦截和 DOM 解析获取活动数据。
    """
    api_items = []
    dom_items = []
    seen_names = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            viewport={"width": 390, "height": 844},
        )
        page = await context.new_page()

        # 拦截 API 响应
        def on_response(resp):
            async def handle():
                try:
                    url = resp.url
                    if "mtop.damai.cn" not in url or "project.classify" not in url:
                        return
                    data = await resp.json()
                    inner = data.get("data", {})
                    for key in ["currentCity", "nearByCity"]:
                        items = inner.get(key, [])
                        for item in items:
                            name = item.get("name", "")
                            if name and name not in seen_names:
                                seen_names.add(name)
                                api_items.append(item)
                except Exception:
                    pass
            asyncio.create_task(handle())

        page.on("response", on_response)

        # 访问首页
        try:
            await page.goto("https://m.damai.cn", wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"大麦首页访问失败: {e}", file=sys.stderr)
            await browser.close()
            return []

        # 切换到目标城市
        try:
            # 点击城市选择按钮
            await page.click('text=北京', timeout=5000)
            await asyncio.sleep(1)
            # 在城市列表中选择目标城市
            city_selector = f'text={city}'
            await page.click(city_selector, timeout=5000)
            await asyncio.sleep(2)
            print(f"已切换城市到: {city}", file=sys.stderr)
        except Exception as e:
            print(f"城市切换失败: {e}，使用默认城市", file=sys.stderr)

        # 从 DOM 提取结构化活动卡片
        dom_events = await page.evaluate('''() => {
            const results = [];
            const cards = document.querySelectorAll('.home_project-item');
            cards.forEach(card => {
                const titleEl = card.querySelector('.project-item_info_title');
                const timeEl = card.querySelector('.project-item_info_time');
                const priceEl = card.querySelector('.project-item_info_price');
                const tagEl = card.querySelector('.project-item_info_tag');
                const linkEl = card.querySelector('a');

                const title = titleEl?.innerText?.trim() || '';
                const rawTime = (timeEl?.innerText || '').trim();

                // 价格：从 .price-tag 中提取
                let priceStr = '';
                const priceWrap = card.querySelector('.price-tag');
                if (priceWrap) {
                    const start = priceWrap.querySelector('.price-start')?.innerText || '';
                    const num = priceWrap.querySelector('.price')?.innerText || '';
                    const end = priceWrap.querySelector('.price-end')?.innerText || '';
                    priceStr = (start + num + end).replace(/\\s/g, '');
                }

                // 标签：从 .normal-tag 等提取
                const tags = [];
                card.querySelectorAll('.normal-tag').forEach(t => {
                    const txt = t.innerText?.trim();
                    if (txt) tags.push(txt);
                });
                const scoreEl = card.querySelector('.project-item_info_score_color');
                if (scoreEl) tags.push('大麦评分 ' + (scoreEl.innerText?.trim() || ''));
                const rankingEl = card.querySelector('.project-item_info_ranking');
                if (rankingEl) tags.push(rankingEl.innerText?.trim() || '');

                const href = linkEl?.href || '';

                // 按换行符拆分时间和地点
                const lines = rawTime.split('\\n').map(l => l.trim()).filter(Boolean);
                let dateStr = '';
                let venueStr = '';
                for (const line of lines) {
                    // 日期行：以 202X 开头
                    if (/^20\\d{2}/.test(line)) {
                        dateStr = line;
                    }
                    // 地点行：包含 | 且不以 202X 开头
                    else if (line.includes('|')) {
                        const parts = line.split('|');
                        venueStr = parts.slice(1).join('|').trim();
                    }
                    // 纯地点行
                    else if (line && !dateStr) {
                        dateStr = line;
                    }
                }

                if (title) {
                    results.push({
                        title,
                        date: dateStr,
                        venue: venueStr,
                        price: priceStr,
                        tags: tags.join(' | '),
                        link: href,
                    });
                }
            });
            return results;
        }''')

        # 合并 DOM 提取结果
        for item in dom_events:
            if item['title'] not in seen_names:
                seen_names.add(item['title'])
                dom_items.append({
                    "name": item['title'],
                    "showTime": item['date'],
                    "venueName": item['venue'],
                    "districtAreaName": "",
                    "priceStr": item['price'],
                    "categoryName": "",
                    "guideCategoryName": "",
                    "commonTags": [{"name": t} for t in item['tags'].split(' | ') if t] if item.get('tags') else [],
                    "rankingList": {},
                    "ipId": extract_item_id(item['link']),
                    "cityName": city,
                })

        await browser.close()

    # 合并 API 和 DOM 数据
    all_raw = api_items + dom_items
    results = []
    for item in all_raw:
        city_name = item.get("cityName", "")
        if city and city not in city_name and city_name:
            continue

        results.append({
            "platform": "大麦",
            "title": item.get("name", ""),
            "date": item.get("showTime", ""),
            "venue": item.get("venueName", ""),
            "district": item.get("districtAreaName", ""),
            "price": item.get("priceStr", ""),
            "category": item.get("categoryName", ""),
            "guide_category": item.get("guideCategoryName", ""),
            "tags": [t.get("name", "") for t in item.get("commonTags", [])],
            "ranking": item.get("rankingList", {}).get("title", ""),
            "link": f"https://m.damai.cn/shows/project.html?itemId={item.get('ipId', '')}" if item.get("ipId") else "",
        })

    return results[:max_items]


async def scrape_huodongxing(city, event_type="全部", max_items=15):
    """
    通过 Playwright 抓取活动行文化活动数据。
    使用城市名称作为 URL 参数，滚动加载更多活动。
    """
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        try:
            await page.goto(
                f"https://www.huodongxing.com/events?city={city}",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            await asyncio.sleep(3)
        except Exception as e:
            print(f"活动行访问失败: {e}", file=sys.stderr)
            await browser.close()
            return []

        # 滚动加载更多内容
        for _ in range(2):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

        items = await page.evaluate("""() => {
            const seen = new Set();
            const results = [];
            document.querySelectorAll('.search-tab-content-item-mesh').forEach(el => {
                const a = el.querySelector('a');
                const href = a ? a.href : '';
                const id = href.split('/event/')[1]?.split('?')[0] || '';
                if (!id || seen.has(id)) return;
                seen.add(id);

                const text = el.innerText || '';
                const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);

                // 解析标签（"早鸟特惠"、"免费" 等）
                const tags = [];
                const badgeEls = el.querySelectorAll('.el-tag, .tag, [class*="badge"]');
                badgeEls.forEach(b => {
                    const t = b.innerText?.trim();
                    if (t) tags.push(t);
                });
                // 从文本行中提取额外标签（不在标题/日期/地点/主办方中的行）
                const knownLines = new Set();
                if (lines.length > 0) knownLines.add(lines[0]); // title
                if (lines.length > 1) knownLines.add(lines[1]); // date
                if (lines.length > 2) knownLines.add(lines[2]); // location
                if (lines.length > 3) knownLines.add(lines[3]); // organizer
                for (const line of lines) {
                    if (!knownLines.has(line) && line && !line.startsWith('粉丝')) {
                        tags.push(line);
                    }
                }

                if (lines.length > 0) {
                    results.push({
                        title: lines[0] || '',
                        date: lines[1] || '',
                        location: lines[2] || '',
                        organizer: lines[3] || '',
                        fans: lines[4] || '',
                        tags: tags.join(', '),
                        link: href,
                    });
                }
            });
            return results;
        }""")

        await browser.close()

    # 文化活动关键词过滤
    cultural_keywords = [
        "书", "读", "文学", "讲座", "沙龙", "分享", "艺术", "展览", "展",
        "音乐", "演出", "话剧", "话剧", "喜剧", "脱口秀", "音乐", "乐队",
        "诗歌", "诗", "文化", "电影", "影视", "手工", "市集", "集市",
        "剧场", "live", "livehouse", "演唱会", "节", "周末", "活动",
    ]

    # 如果指定了活动类型，进行更严格的过滤
    type_keywords = {
        "展览": ["展览", "展", "博览会", "art", "画廊", "美术馆"],
        "音乐会": ["音乐", "演唱会", "乐队", "live", "音乐会", "演奏"],
        "话剧": ["话剧", "舞台剧", "音乐剧", "剧场", "戏剧"],
        "脱口秀": ["脱口秀", "喜剧", "开放麦", "Stand-up"],
        "讲座": ["讲座", "沙龙", "分享会", "读书会", "读书会", "书"],
        "音乐节": ["音乐节", "fest", "节"],
    }

    for item in items[:max_items]:
        title = item.get("title", "")
        organizer = item.get("organizer", "")
        text_content = title + organizer

        # 基础文化过滤：至少匹配一个文化关键词
        if not any(kw.lower() in text_content.lower() for kw in cultural_keywords):
            continue

        # 如果指定了类型，进一步过滤
        if event_type != "全部" and event_type in type_keywords:
            if not any(kw.lower() in text_content.lower() for kw in type_keywords[event_type]):
                continue

        results.append({
            "platform": "活动行",
            "title": title,
            "date": item["date"],
            "venue": item["location"],
            "district": "",
            "price": "",
            "category": "",
            "guide_category": "",
            "tags": [item["organizer"]] + ([item["fans"]] if item.get("fans") else []),
            "ranking": "",
            "link": item["link"],
        })

    return results


# 常用城市中文名到豆瓣同城 URL slug 的映射
DOUBAN_CITY_MAP = {
    "北京": "beijing",
    "上海": "shanghai",
    "广州": "guangzhou",
    "深圳": "shenzhen",
    "成都": "chengdu",
    "杭州": "hangzhou",
    "南京": "nanjing",
    "重庆": "chongqing",
    "武汉": "wuhan",
    "西安": "xian",
    "苏州": "suzhou",
    "天津": "tianjin",
    "长沙": "changsha",
    "青岛": "qingdao",
    "大连": "dalian",
    "厦门": "xiamen",
    "昆明": "kunming",
    "郑州": "zhengzhou",
    "济南": "jinan",
    "合肥": "hefei",
}


def _get_douban_city_slug(city):
    """获取豆瓣同城 URL 中使用的城市 slug（拼音）。"""
    slug = DOUBAN_CITY_MAP.get(city)
    if slug:
        return slug
    # 回退：尝试用 pypinyin 转换
    try:
        from pypinyin import pinyin, Style
        parts = pinyin(city, style=Style.NORMAL)
        return "".join(p[0] for p in parts)
    except ImportError:
        return city  # 无法转换则使用原名（可能 404）


async def scrape_douban(city, event_type="全部", max_items=15):
    """
    通过 Playwright 抓取豆瓣同城活动数据。
    """
    results = []
    city_slug = _get_douban_city_slug(city)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        try:
            await page.goto(
                f"https://www.douban.com/location/{city_slug}/events/",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            await asyncio.sleep(2)
        except Exception as e:
            print(f"豆瓣同城访问失败: {e}", file=sys.stderr)
            await browser.close()
            return []

        items = await page.evaluate('''() => {
            const results = [];
            const entries = document.querySelectorAll('li.list-entry');
            entries.forEach(entry => {
                const titleEl = entry.querySelector('.title a');
                const title = titleEl?.innerText?.trim() || '';
                const link = titleEl?.href || '';

                const timeEl = entry.querySelector('.event-time');
                const timeStr = timeEl?.innerText?.replace('时间：', '')?.trim() || '';

                const locEl = entry.querySelector('.event-meta li[title]');
                const locationStr = locEl?.innerText?.replace('地点：', '')?.trim() || '';

                const text = entry.innerText || '';
                const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
                let costStr = '';
                let organizerStr = '';
                for (const line of lines) {
                    if (line.startsWith('费用：')) {
                        costStr = line.replace('费用：', '').trim();
                    } else if (line.startsWith('发起：')) {
                        organizerStr = line.replace('发起：', '').trim();
                    }
                }

                if (title) {
                    results.push({
                        title,
                        time: timeStr,
                        location: locationStr,
                        cost: costStr,
                        organizer: organizerStr,
                        link,
                    });
                }
            });
            return results;
        }''')

        await browser.close()

    for item in items[:max_items]:
        results.append({
            "platform": "豆瓣同城",
            "title": item["title"],
            "date": item["time"],
            "venue": item["location"],
            "district": "",
            "price": item["cost"],
            "category": "",
            "guide_category": "",
            "tags": [item["organizer"]] if item["organizer"] else [],
            "ranking": "",
            "link": item["link"],
        })

    return results


def extract_item_id(url):
    """从链接 URL 中提取 itemId"""
    if not url:
        return None
    match = re.search(r'itemId=(\d+)', url)
    return match.group(1) if match else None


def categorize_events(events):
    """将活动按类型分类，演唱会/音乐节放最后（需提前购票）"""
    categories = {
        "展览": [],
        "话剧/音乐剧": [],
        "脱口秀/喜剧": [],
        "演唱会/音乐节": [],
        "其他": [],
    }

    music_keywords = ["演唱会", "音乐节", "音乐会", "LIVE", "Livehouse", "live"]

    for event in events:
        guide = event.get("guide_category", "")
        category = event.get("category", "")
        title = event.get("title", "")

        if guide in ("音乐现场", "音乐会") or category in ("演唱会", "音乐节", "音乐会") or any(kw.lower() in title.lower() for kw in music_keywords):
            categories["演唱会/音乐节"].append(event)
        elif guide == "话剧音乐剧" or category in ["话剧歌剧"] or any(kw in title for kw in ["话剧", "音乐剧", "舞台剧"]):
            categories["话剧/音乐剧"].append(event)
        elif guide == "展览" or category in ["展览休闲"] or "展览" in title:
            categories["展览"].append(event)
        elif guide == "脱口秀" or any(kw in title for kw in ["脱口秀", "喜剧", "单口"]):
            categories["脱口秀/喜剧"].append(event)
        else:
            categories["其他"].append(event)

    return {k: v for k, v in categories.items() if v}


def format_as_markdown(output):
    """将活动数据格式化为 Markdown 表格输出"""
    lines = []
    city = output.get("city", "")
    search_date = output.get("search_date", "")
    total = output.get("total", 0)

    lines.append(f"# {city}文化活动推荐\n")
    lines.append(f"> 搜索日期：{search_date} | 共推荐 **{total}** 场活动\n")

    categories = output.get("categories", {})
    if not categories:
        lines.append("暂无活动数据。")
        return "\n".join(lines)

    for cat_name, events in categories.items():
        lines.append(f"\n## {cat_name}\n")
        if not events:
            lines.append("该分类暂无活动。\n")
            continue

        lines.append("| 活动名称 | 时间 | 地点 | 票价 | 来源 | 链接 |")
        lines.append("|----------|------|------|------|------|------|")

        for ev in events:
            title = ev.get("title", "")
            # 标注排行榜
            ranking = ev.get("ranking", "")
            if ranking:
                title = f"{title} 🏆{ranking}"

            date = ev.get("date", "")
            venue = ev.get("venue", "")
            district = ev.get("district", "")
            if district:
                venue = f"{district} {venue}"
            price = ev.get("price", "")
            platform = ev.get("platform", "")

            link = ev.get("link", "")
            link_text = "[购票/详情]({})".format(link) if link else "-"

            # 清理管道符避免破坏表格结构
            title = title.replace("|", "｜")
            venue = venue.replace("|", "｜")

            lines.append(f"| {title} | {date} | {venue} | {price} | {platform} | {link_text} |")

        lines.append("")

    return "\n".join(lines)


async def main():
    # 解析参数：支持 --format json|markdown
    args = sys.argv[1:]
    flags = {}
    positional = []
    i = 0
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i].lstrip("-")
            val = "true"
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                val = args[i + 1]
                i += 1
            flags[key] = val
        else:
            positional.append(args[i])
        i += 1

    if not positional:
        print(json.dumps({"error": "请提供城市名称，如: python3 scrape_events.py 北京"}))
        sys.exit(1)

    city = positional[0]
    event_type = positional[1] if len(positional) > 1 else "全部"
    max_items = int(positional[2]) if len(positional) > 2 else 20
    output_format = flags.get("format", "json")

    print(f"正在抓取 {city} 的{event_type}活动数据...", file=sys.stderr)

    # 并行抓取大麦、豆瓣和活动行
    damai_task = scrape_damai(city, event_type=event_type, max_items=max_items)
    douban_task = scrape_douban(city, event_type=event_type, max_items=max_items // 2)
    hdx_task = scrape_huodongxing(city, event_type=event_type, max_items=max_items // 2)
    damai_events, douban_events, hdx_events = await asyncio.gather(
        damai_task, douban_task, hdx_task, return_exceptions=True
    )

    if isinstance(damai_events, Exception):
        damai_events = []
    if isinstance(douban_events, Exception):
        douban_events = []
    if isinstance(hdx_events, Exception):
        hdx_events = []

    events = damai_events + douban_events + hdx_events

    categorized = categorize_events(events)

    output = {
        "city": city,
        "type": event_type,
        "search_date": datetime.now().strftime("%Y-%m-%d"),
        "total": len(events),
        "categories": categorized,
    }

    if output_format == "markdown":
        print(format_as_markdown(output))
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
