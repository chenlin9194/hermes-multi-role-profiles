#!/bin/bash
set -e

# ==========================================
# Hermes DNS 稳定性修复脚本
# 修复 WSL2 DNS 代理不稳定导致飞书 WebSocket 断连
# ==========================================

# 备份当前配置
echo "[1/4] 备份当前配置..."
cp /etc/resolv.conf /home/linchen/.hermes/backup/dns_backup_20260430/resolv.conf.bak 2>/dev/null || true
cp /etc/wsl.conf /home/linchen/.hermes/backup/dns_backup_20260430/wsl.conf.bak 2>/dev/null || true
echo "      备份位置: /home/linchen/.hermes/backup/dns_backup_20260430/"

# 更新 wsl.conf - 禁止自动生成 resolv.conf
echo "[2/4] 更新 /etc/wsl.conf..."
cat > /etc/wsl.conf << 'WSLEND'
[user]
default=ubuntu
[boot]
systemd=true
[network]
generateResolvConf = false
WSLEND

# 替换 resolv.conf 为稳定 DNS
echo "[3/4] 替换 /etc/resolv.conf..."
rm -f /etc/resolv.conf
cat > /etc/resolv.conf << 'RESOLV'
nameserver 8.8.8.8
nameserver 1.1.1.1
RESOLV

# 锁定 resolv.conf
echo "[4/4] 锁定 /etc/resolv.conf 防止被覆盖..."
chattr +i /etc/resolv.conf

echo ""
echo "✅ DNS 修复完成！"
echo "   当前 DNS: $(cat /etc/resolv.conf | grep nameserver)"
echo ""
echo "⚠️  /etc/wsl.conf 的修改需要重启 WSL 才完全生效。"
echo "   重启命令: wsl --shutdown && 重新打开终端"
echo "   resolv.conf 已立即生效，Hermes 不需要重启。"
echo ""
echo "如需回滚: bash /home/linchen/.hermes/scripts/rollback_dns.sh"
