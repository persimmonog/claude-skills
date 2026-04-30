#!/usr/bin/env python3
"""
Marauders Map — HTML Generator
Usage:
  python generate_html.py --events '[...]' --title "广州近期活动" --output /mnt/user-data/outputs/marauders_map.html
"""
import argparse
import json
import sys

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>活动地图</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<style>
  @import url('https://fonts.loli.net/css2?family=Cinzel:wght@400;700&family=Noto+Serif+SC:wght@400;700&display=swap');
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#1a0e00; font-family:'Noto Serif SC',serif; overflow:hidden; }

  #map {
    width:100vw; height:100vh;
    filter: sepia(0.85) contrast(1.08) brightness(0.82) saturate(0.6) hue-rotate(-8deg);
  }
  #vignette {
    position:fixed; inset:0; pointer-events:none; z-index:500;
    background: radial-gradient(ellipse at 50% 50%,
      transparent 38%, rgba(30,10,0,0.50) 75%, rgba(10,3,0,0.80) 100%);
  }
  #grain {
    position:fixed; inset:0; pointer-events:none; z-index:501; opacity:0.04;
    background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    background-size:180px 180px;
  }

  /* ── Footer ─────────────────────────────────────── */
  #footer {
    position:fixed; bottom:0; left:0; right:0; z-index:600;
    text-align:center; padding:6px 20px 10px;
    background:linear-gradient(0deg,rgba(15,5,0,0.88) 0%,rgba(15,5,0,0.55) 80%,transparent 100%);
    pointer-events:none;
    font-size:clamp(7px,1.6vw,10px); color:#7a5c20;
    font-style:italic; letter-spacing:0.18em;
  }

  /* ── Marker ─────────────────────────────────────── */
  .mm-marker { position:relative; width:36px; height:36px; transform:translate(-50%,-50%); }
  .mm-pulse {
    position:absolute; inset:-5px; border-radius:50%;
    border:1.5px solid rgba(200,168,74,0.35);
    animation:pulse 2.8s ease-out infinite;
  }
  .mm-inner {
    width:34px; height:34px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    border:2px solid rgba(245,224,176,0.80);
    box-shadow:0 0 12px rgba(200,168,74,0.45), 0 3px 8px rgba(0,0,0,0.65);
    font-size:13px; font-weight:700; color:#f5e0b0;
    font-family:'Cinzel',serif; cursor:pointer;
    transition:transform 0.18s, box-shadow 0.18s;
  }
  .mm-inner:hover {
    transform:scale(1.18);
    box-shadow:0 0 18px rgba(200,168,74,0.70), 0 3px 10px rgba(0,0,0,0.7);
  }
  @keyframes pulse {
    0%   { transform:scale(0.92); opacity:0.75; }
    65%  { transform:scale(1.50); opacity:0; }
    100% { transform:scale(0.92); opacity:0; }
  }

  /* ── Popup ──────────────────────────────────────── */
  .leaflet-popup-content-wrapper {
    background:rgba(22,10,0,0.95) !important;
    border:1px solid rgba(122,92,30,0.7) !important;
    border-radius:5px !important;
    box-shadow:0 6px 24px rgba(0,0,0,0.75), 0 0 14px rgba(200,168,74,0.18) !important;
  }
  .leaflet-popup-content { margin:12px 16px !important; }
  .leaflet-popup-tip-container { display:none; }
  .leaflet-popup-close-button { color:#a07838 !important; font-size:16px !important; top:6px !important; right:8px !important; }
  .mm-popup-name {
    font-family:'Cinzel','Noto Serif SC',serif;
    font-size:14px; font-weight:700; color:#c8a84a;
    margin-bottom:6px;
    text-shadow:0 0 8px rgba(200,168,74,0.35);
    line-height:1.3;
  }
  .mm-popup-venue { font-size:11px; color:#a08040; margin-bottom:4px; font-style:italic; }
  .mm-popup-date  { font-size:10px; color:#806030; margin-bottom:6px; }
  .mm-popup-tag {
    display:inline-block; font-size:9px; padding:2px 8px;
    border-radius:10px; border:1px solid; letter-spacing:0.08em;
  }

  /* ── Legend ─────────────────────────────────────── */
  #legend {
    position:fixed; bottom:44px; left:14px; z-index:600;
    background:rgba(16,6,0,0.90); border:1px solid rgba(122,92,30,0.55);
    border-radius:4px; padding:10px 13px; min-width:128px;
    box-shadow:0 4px 18px rgba(0,0,0,0.55);
  }
  #legend h4 {
    font-family:'Cinzel','Noto Serif SC',serif;
    font-size:10px; color:#c8a84a; margin-bottom:7px; letter-spacing:0.12em;
  }
  .leg-row { display:flex; align-items:center; gap:7px; margin-bottom:5px; font-size:10px; color:#a08040; }
  .leg-dot {
    width:14px; height:14px; border-radius:50%;
    border:1.5px solid rgba(245,224,176,0.65); flex-shrink:0;
    display:flex; align-items:center; justify-content:center;
    font-size:7px; font-weight:700; color:#f5e0b0; font-family:'Cinzel',serif;
  }

  /* ── Leaflet zoom tweak ─────────────────────────── */
  .leaflet-control-zoom { margin-top:10px !important; }
  .leaflet-control-zoom a {
    background:rgba(16,6,0,0.85) !important; color:#c8a84a !important;
    border-color:rgba(122,92,30,0.5) !important;
  }
  .leaflet-control-zoom a:hover { background:rgba(40,18,0,0.95) !important; }
</style>
</head>
<body>

<div id="map"></div>
<div id="vignette"></div>
<div id="grain"></div>

<div id="footer">～ 以魔法之眼，观世间百态 · I solemnly swear that I am up to no good ～</div>

<div id="legend">
  <h4>图 例</h4>
  {{LEGEND_HTML}}
</div>

<script>
const events = {{EVENTS_JSON}};

const TYPE = {
  concert:    {color:"#7B1A1A", label:"演出/音乐",   sym:"M"},
  theater:    {color:"#1E4A1E", label:"话剧/戏曲",   sym:"T"},
  bookclub:   {color:"#1A1A6E", label:"读书/讲座",   sym:"B"},
  comedy:     {color:"#6E3A0A", label:"喜剧/脱口秀", sym:"C"},
  exhibition: {color:"#3A1A6E", label:"展览/美术",   sym:"E"},
  other:      {color:"#2A2A2A", label:"其他活动",    sym:"*"},
};

const avgLat = events.reduce((s,e)=>s+e.lat,0)/events.length;
const avgLon = events.reduce((s,e)=>s+e.lon,0)/events.length;

const map = L.map('map', {
  center:[avgLat, avgLon], zoom:13,
  zoomControl:false, attributionControl:false,
});

L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
  attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
  maxZoom:19, subdomains:'abcd',
}).addTo(map);

L.control.zoom({position:'topright'}).addTo(map);

events.forEach(ev => {
  const t = TYPE[ev.type] || TYPE.other;
  const icon = L.divIcon({
    className:'',
    html:`<div class="mm-marker"><div class="mm-pulse"></div><div class="mm-inner" style="background:${t.color}">${t.sym}</div></div>`,
    iconSize:[36,36], iconAnchor:[18,18],
  });
  const dateRow = ev.date ? `<div class="mm-popup-date">🗓 ${ev.date}</div>` : '';
  const popup = L.popup({maxWidth:220, offset:[0,-12]}).setContent(
    `<div class="mm-popup-name">${ev.name}</div>
     <div class="mm-popup-venue">📍 ${ev.venue}</div>
     ${dateRow}
     <span class="mm-popup-tag" style="color:${t.color};border-color:${t.color}">${t.label}</span>`
  );
  L.marker([ev.lat,ev.lon],{icon}).bindPopup(popup).addTo(map);
});

const bounds = L.latLngBounds(events.map(e=>[e.lat,e.lon]));
if (events.length === 1) {
  map.setView([events[0].lat, events[0].lon], 15);
} else {
  map.fitBounds(bounds, {padding:[70,70]});
}
</script>
</body>
</html>
"""

TYPE_LABELS = {
    "concert":    ("演出/音乐",   "#7B1A1A", "M"),
    "theater":    ("话剧/戏曲",   "#1E4A1E", "T"),
    "bookclub":   ("读书/讲座",   "#1A1A6E", "B"),
    "comedy":     ("喜剧/脱口秀", "#6E3A0A", "C"),
    "exhibition": ("展览/美术",   "#3A1A6E", "E"),
    "other":      ("其他活动",    "#2A2A2A", "*"),
}


def build_legend_html(events: list[dict]) -> str:
    seen = []
    for ev in events:
        t = ev.get("type", "other")
        if t not in seen:
            seen.append(t)
    rows = []
    for t in seen:
        label, color, sym = TYPE_LABELS.get(t, ("其他", "#2A2A2A", "*"))
        rows.append(
            f'<div class="leg-row">'
            f'<div class="leg-dot" style="background:{color}">{sym}</div>'
            f'{label}</div>'
        )
    return "\n  ".join(rows)


def normalize_event(ev: dict) -> dict:
    """Normalize event fields: scrape_events uses 'title', marauders-map uses 'name'."""
    result = dict(ev)
    if "title" in result and "name" not in result:
        result["name"] = result.pop("title")
    return result


def generate(events: list[dict], output_path: str):
    events = [normalize_event(e) for e in events]
    events_json = json.dumps(events, ensure_ascii=False)
    legend_html = build_legend_html(events)
    html = (HTML_TEMPLATE
            .replace("{{EVENTS_JSON}}", events_json)
            .replace("{{LEGEND_HTML}}", legend_html))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[marauders-map] HTML saved → {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True)
    parser.add_argument("--output", default="/mnt/user-data/outputs/marauders_map.html")
    args = parser.parse_args()
    events = json.loads(args.events)
    generate(events, args.output)
