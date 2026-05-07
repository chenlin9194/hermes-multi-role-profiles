#!/bin/bash
set -e

echo "[1/4] 备份当前配置..."
cp /etc/resolv.conf /home/linchen/.hermes/backup/dns_backup_20260430/resolv.conf.bak 2>/dev/null || true
cp /etc/wsl.conf /home/linchen/.hermes/backup/dns_backup_20260430/wsl.conf.bak 2>/dev/null || true
echo "      备份位置: /home/linchen/.hermes/backup/dns_backup_20260430/"

echo "[2/4] 写入 /etc/wsl.conf..."
echo '[user]
default=ubuntu
[boot]
systemd=true
[network]
generateResolvConf = false' | tee /etc/wsl.conf > /dev/null

echo "[3/4] 替换 /etc/resolv.conf..."
# 删除旧的软链，创建独立文件
rm -f /etc/resolv.conf
echo 'nameserver 8.8.8.8
nameserver 1.1.1.1' | tee /etc/resolv.conf > /dev/null

echo "[4/4] 锁定 resolv.conf 防止被覆盖..."
chattr +i /etc/resolv.conf

echo ""
echo "✅ DNS 修复完成！"
echo "   当前 DNS: $(grep nameserver /etc/resolv.conf)"
echo ""
echo "如需回滚: bash /home/linchen/.hermes/scripts/rollback_dns_v2.sh"
