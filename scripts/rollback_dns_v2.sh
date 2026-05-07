#!/bin/bash
set -e

BACKUP_DIR=/home/linchen/.hermes/backup/dns_backup_20260430

echo "[1/3] 解锁并删除 resolv.conf..."
chattr -i /etc/resolv.conf 2>/dev/null || true
rm -f /etc/resolv.conf

echo "[2/3] 恢复 wsl.conf..."
if [ -f "$BACKUP_DIR/wsl.conf.bak" ]; then
    cp "$BACKUP_DIR/wsl.conf.bak" /etc/wsl.conf
    echo "      wsl.conf 已恢复"
else
    echo "      无备份，跳过"
fi

echo "[3/3] 重启 WSL 网络栈以重新生成 resolv.conf..."
# 删除后 WSL 会自动重新创建 /etc/resolv.conf 软链
# 用户需要重启 WSL
echo ""
echo "✅ 已回滚。请重启 WSL 使配置生效："
echo "   wsl --shutdown && 重新打开终端"
echo ""
echo "WSL 重启后，resolv.conf 会自动恢复为 WSL 管理的默认配置。"
