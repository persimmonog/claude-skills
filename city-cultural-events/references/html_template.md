# HTML 地图模板说明

完整模板见 `scripts/generate_html.py` 中的 `HTML_TEMPLATE` 字符串。
以下说明关键设计决策，便于理解和修改。

## 羊皮纸效果实现

```css
#map {
  filter: sepia(0.85) contrast(1.08) brightness(0.82) saturate(0.6) hue-rotate(-8deg);
}
```
这一组 CSS filter 叠加在整个 Leaflet 地图 div 上，将 OSM 彩色地图变为泛黄古旧风格。
数值说明：
- `sepia(0.85)`：主色调转棕黄
- `brightness(0.82)`：压暗，避免刺眼
- `saturate(0.6)`：降低饱和度，使色彩更沉稳
- `hue-rotate(-8deg)`：色相微调，偏暖

## 晕影（Vignette）

```css
background: radial-gradient(ellipse at 50% 50%,
  transparent 40%, rgba(30,10,0,0.55) 80%, rgba(10,3,0,0.82) 100%);
```
独立的 `position:fixed` div，`pointer-events:none`，不影响地图交互。

## 标记图标（DivIcon）

使用 Leaflet `L.divIcon` 而非默认图钉，生成带脉冲动画的圆形标记：
- 外圈：CSS `@keyframes pulse` 淡出扩散环
- 内圈：彩色圆形 + 类型符号字母

## 弹窗（Popup）

通过 `.leaflet-popup-content-wrapper` 覆盖 Leaflet 默认样式，改为深色半透明背景。
弹窗内容包含：活动名、场馆、可选日期、类型标签。

## 字体加载

```css
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Noto+Serif+SC:wght@400;700&display=swap');
```
- `Cinzel`：拉丁哥特感衬线体，用于标题和标记符号
- `Noto Serif SC`：中文衬线体，用于活动名称和说明文字

## JS 数据注入位置

在 `<script>` 块顶部，`const events = [...];` 这一行由 `generate_html.py` 动态替换为实际数据。
