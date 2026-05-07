#!/bin/bash
set -e

# ==========================================
# Hermes DNS 回滚脚本
# ==========================================

BACKUP_DIR=/home/linchen/.hermes/backup/dns_backup_20260430

echo "[1/3] 解锁 resolv.conf..."
chattr -i /etc/resolv.conf

echo "[2/3] 恢复 resolv.conf..."
if [ -f "$BACKUP_DIR/resolv.conf.bak" ]; then
    cp "$BACKUP_DIR/resolv.conf.bak" /etc/resolv.conf
    echo "      已恢复"
fi

echo "[3/3] 恢复 wsl.conf..."
if [ -f "$BACKUP_DIR/wsl.conf.bak" ]; then
    cp "$BACKUP_DIR/wsl.conf.bak" /etc/wsl.conf
    echo "      已恢复"
fi

echo ""
echo "✅ 已回滚到备份状态。建议重启 WSL 使 wsl.conf 生效:"
echo "   wsl --shutdown && 重新打开终端"
