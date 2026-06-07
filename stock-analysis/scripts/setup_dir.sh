#!/usr/bin/env bash
# ============================================================================
# stock-analysis 分析文件夹创建脚本
# ============================================================================
# 用法: bash scripts/setup_dir.sh <公司中文名>
# 示例: bash scripts/setup_dir.sh "名创优品"
# ============================================================================

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "用法: bash setup_dir.sh <公司中文名>"
    echo "示例: bash setup_dir.sh "名创优品""
    exit 1
fi

COMPANY_NAME="$1"
BASE_DIR="stock-analysis/${COMPANY_NAME}"

mkdir -p "${BASE_DIR}/source_docs"

echo "========================================"
echo "📁 分析文件夹已创建"
echo "   ${BASE_DIR}/"
echo "       ├── report.md        ← 待生成"
echo "       ├── critical_data.md ← 待生成"
echo "       └── source_docs/     ← 原始文档存放"
echo "========================================"
