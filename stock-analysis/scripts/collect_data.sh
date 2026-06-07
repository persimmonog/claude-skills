#!/usr/bin/env bash
# ============================================================================
# stock-analysis 数据采集脚本
# 一次性执行所有 Longbridge CLI 数据采集命令，并行执行，保存到指定目录
# ============================================================================
# 用法:
#   bash scripts/collect_data.sh <SYMBOL> <OUTPUT_DIR>
#
# 示例:
#   bash scripts/collect_data.sh MNSO.US stock-analysis/名创优品/
#   bash scripts/collect_data.sh 700.HK stock-analysis/腾讯/
#
# 输出到 OUTPUT_DIR/data/ 下:
#   ├── quote.txt          行情价格
#   ├── kline.txt          K线历史（周线一年）
#   ├── financial_IS.txt   利润表（年报）
#   ├── financial_BS.txt   资产负债表（年报）
#   ├── financial_CF.txt   现金流量表（年报）
#   ├── financial_Q.txt    利润表（季度）
#   ├── calc_index.txt     核心估值指标
#   ├── valuation.txt      估值深度分析
#   ├── consensus.txt      分析师一致预期
#   ├── company.txt        公司概览
#   ├── executive.txt      管理层名单
#   ├── shareholder.txt    前十大股东
#   ├── dividend.txt       分红记录
#   ├── institution.txt    机构评级
#   ├── industry_val.txt   行业估值对比
#   ├── insider.txt        内部人交易（美股）
#   ├── news.txt           最新新闻
#   └── topic.txt          社区讨论
# ============================================================================

set -uo pipefail

if [ $# -lt 2 ]; then
    echo "用法: bash collect_data.sh <SYMBOL> <OUTPUT_DIR>"
    echo "示例: bash collect_data.sh MNSO.US stock-analysis/名创优品/"
    exit 1
fi

SYMBOL="$1"
OUTPUT_DIR="$2"
DATA_DIR="${OUTPUT_DIR}/data"

mkdir -p "$DATA_DIR"

# 跨平台日期计算（macOS / Linux）
START=$(python3 -c "import datetime; print((datetime.date.today() - datetime.timedelta(days=365)).strftime('%Y-%m-%d'))")
END=$(date +%Y-%m-%d)

echo "========================================"
echo "📊 数据采集: $SYMBOL"
echo "输出目录: $DATA_DIR"
echo "========================================"
echo "⏳ 并行采集所有模块中..."

# ── 并行启动辅助 ──
pids=()
sfs=()

run() {
    local label="$1" out="$2"; shift 2
    local sf="${out}.status"
    sfs+=("$sf")
    ( "$@" > "$out" 2>&1 && echo "✅ ${label}" > "$sf" || echo "⚠️ ${label}" > "$sf" ) &
    pids+=($!)
}

# ── 模块 A：行情与价格 ──
run "quote.txt"           "${DATA_DIR}/quote.txt"           longbridge quote "$SYMBOL"
run "kline.txt"           "${DATA_DIR}/kline.txt"           longbridge kline history "$SYMBOL" --start "$START" --end "$END" --period week

# ── 模块 B：财务报表 ──
run "financial_IS.txt"    "${DATA_DIR}/financial_IS.txt"    longbridge financial-report "$SYMBOL" --kind IS --report af
run "financial_Q.txt"     "${DATA_DIR}/financial_Q.txt"     longbridge financial-report "$SYMBOL" --kind IS --report qf
run "financial_BS.txt"    "${DATA_DIR}/financial_BS.txt"    longbridge financial-report "$SYMBOL" --kind BS --report af
run "financial_CF.txt"    "${DATA_DIR}/financial_CF.txt"    longbridge financial-report "$SYMBOL" --kind CF --report af

# ── 模块 C：估值指标 ──
run "calc_index.txt"      "${DATA_DIR}/calc_index.txt"      longbridge calc-index "$SYMBOL"
run "valuation.txt"       "${DATA_DIR}/valuation.txt"       longbridge valuation "$SYMBOL"
run "consensus.txt"       "${DATA_DIR}/consensus.txt"       longbridge consensus "$SYMBOL"

# ── 模块 D：公司信息与治理 ──
run "company.txt"         "${DATA_DIR}/company.txt"         longbridge company "$SYMBOL"
run "executive.txt"       "${DATA_DIR}/executive.txt"       longbridge executive "$SYMBOL"
run "shareholder.txt"     "${DATA_DIR}/shareholder.txt"     longbridge shareholder "$SYMBOL"
run "dividend.txt"        "${DATA_DIR}/dividend.txt"        longbridge dividend "$SYMBOL"

# ── 模块 E：机构评级与行业估值 ──
run "institution.txt"     "${DATA_DIR}/institution.txt"     longbridge institution-rating "$SYMBOL"
run "industry_val.txt"    "${DATA_DIR}/industry_val.txt"    bash -c "longbridge industry-valuation '$SYMBOL' > '${DATA_DIR}/industry_val.txt' && longbridge industry-valuation dist '$SYMBOL' >> '${DATA_DIR}/industry_val.txt'"

# ── 模块 F：内部人交易（仅美股） ──
if [[ "$SYMBOL" == *.US ]]; then
    run "insider.txt" "${DATA_DIR}/insider.txt" longbridge insider-trades "$SYMBOL" --count 20
fi

# ── 模块 G：新闻与研究 ──
run "news.txt"            "${DATA_DIR}/news.txt"            longbridge news "$SYMBOL"
run "topic.txt"           "${DATA_DIR}/topic.txt"           longbridge topic "$SYMBOL"

# ── 等待全部完成 ──
for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null; done

# ── 输出结果 ──
echo ""
echo "── 采集结果 ──"
for sf in "${sfs[@]}"; do cat "$sf" 2>/dev/null; rm -f "$sf"; done

echo ""
echo "========================================"
echo "✅ 数据采集完成"
echo "📁 数据保存到: ${DATA_DIR}/"
ls -lh "${DATA_DIR}/" | awk '{print "   " $9 " (" $5 ")"}'
echo "========================================"
