#!/bin/bash
# PaperWiki Launcher (macOS)
# 双击此文件即可启动 PaperWiki 监控服务

# 获取脚本所在目录（即解压后的 PaperWiki 目录）
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "=========================================="
echo "  PaperWiki - 论文自动处理服务"
echo "  配置: $DIR/config.yaml"
echo "=========================================="

# 检查 config.yaml
if [ ! -f "config.yaml" ]; then
    echo "[错误] 未找到 config.yaml，请先配置！"
    echo "将 config.yaml.example 重命名为 config.yaml，然后编辑填写你的配置。"
    read -p "按回车键退出..."
    exit 1
fi

# 启动
if [ -f "paperwiki" ]; then
    echo "[启动] 开始监控论文目录..."
    ./paperwiki
elif [ -f "paperwiki/paperwiki" ]; then
    echo "[启动] 开始监控论文目录..."
    ./paperwiki/paperwiki
else
    echo "[错误] 未找到 paperwiki 可执行文件"
    read -p "按回车键退出..."
    exit 1
fi

echo "PaperWiki 已停止"
read -p "按回车键退出..."
